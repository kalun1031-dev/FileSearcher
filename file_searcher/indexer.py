# -*- coding: utf-8 -*-
"""
文件索引引擎
- os.scandir 扫描：Windows 下从目录枚举直接取得 stat 信息，无需逐文件系统调用
- 多线程目录队列：多个线程并行消费待扫描目录
- 磁盘缓存：pickle 序列化，启动秒级加载
"""
import os
import time
import struct
import pickle
import queue
import threading

from .utils import get_file_extension, get_file_category

# Windows 文件属性
FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_SYSTEM = 0x4
FILE_ATTRIBUTE_REPARSE_POINT = 0x400  # 符号链接/挂接点，跳过避免循环

SCAN_WORKERS = 6


class FileIndex:
    """文件索引条目"""
    __slots__ = ('name', 'path', 'size', 'mtime', 'ext', 'category', 'is_dir')

    def __init__(self, name, path, size, mtime, ext, category, is_dir=False):
        self.name = name
        self.path = path
        self.size = size
        self.mtime = mtime
        self.ext = ext
        self.category = category
        self.is_dir = is_dir

    def to_dict(self):
        return {
            'name': self.name,
            'path': self.path,
            'size': self.size,
            'mtime': self.mtime,
            'ext': self.ext,
            'category': self.category,
            'is_dir': self.is_dir,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            name=d['name'],
            path=d['path'],
            size=d['size'],
            mtime=d['mtime'],
            ext=d['ext'],
            category=d['category'],
            is_dir=d.get('is_dir', False)
        )


class IndexEngine:
    """文件索引引擎"""

    INDEX_VERSION = 2  # v2: scandir + 跳过重解析点，需重建

    def __init__(self, settings):
        self.settings = settings
        self.files = []
        self._lock = threading.Lock()
        self._indexing = False
        self._stop_flag = threading.Event()
        self._progress = 0
        self._status = "未索引"
        self._file_count = 0
        self._index_time = 0
        self.category_counts = None

    # ---------- 状态 ----------
    @property
    def is_indexing(self):
        return self._indexing

    @property
    def status(self):
        return self._status

    @property
    def file_count(self):
        return self._file_count

    @property
    def index_time(self):
        return self._index_time

    def stop(self):
        self._stop_flag.set()

    # ---------- 缓存 ----------
    def load_cache(self):
        cache_file = self.settings.index_file
        if not os.path.exists(cache_file):
            return False

        try:
            with open(cache_file, 'rb') as f:
                version = struct.unpack('I', f.read(4))[0]
                if version != self.INDEX_VERSION:
                    return False
                data_len = struct.unpack('Q', f.read(8))[0]
                data = f.read(data_len)
                files_data = pickle.loads(data)

                with self._lock:
                    self.files = [FileIndex.from_dict(d) for d in files_data]
                    self._file_count = len(self.files)

            self._status = f"已加载 {self._file_count:,} 个文件索引"
            self._compute_counts_async()
            return True
        except Exception:
            return False

    def save_cache(self):
        try:
            with self._lock:
                files_data = [f.to_dict() for f in self.files]
            data = pickle.dumps(files_data, protocol=pickle.HIGHEST_PROTOCOL)
            tmp = self.settings.index_file + '.tmp'
            with open(tmp, 'wb') as f:
                f.write(struct.pack('I', self.INDEX_VERSION))
                f.write(struct.pack('Q', len(data)))
                f.write(data)
            os.replace(tmp, self.settings.index_file)
            return True
        except Exception:
            return False

    # ---------- 索引构建 ----------
    def build_index(self):
        """启动索引线程（UI 通过轮询 status/file_count 获取进度）"""
        if self._indexing:
            return
        self._stop_flag.clear()
        self._indexing = True
        self._progress = 0
        self._file_count = 0
        self._status = "正在建立索引..."
        threading.Thread(target=self._build_worker, daemon=True).start()

    def _build_worker(self):
        try:
            t0 = time.time()

            roots = self.settings.get("index_drives", [])
            if not roots:
                from .utils import get_drives
                roots = get_drives()
            roots = [r for r in roots if os.path.exists(r)]

            exclude = {d.lower() for d in self.settings.get("exclude_dirs", [])}
            skip_hidden = self.settings.get("exclude_hidden", True)
            skip_system = self.settings.get("exclude_system", True)
            include_dirs = not self.settings.get("index_files_only", True)

            stop = self._stop_flag
            work = queue.Queue()
            for r in roots:
                work.put(os.path.abspath(r))
            pending = [len(roots)]
            pending_lock = threading.Lock()
            found = []
            found_lock = threading.Lock()
            counter = [0]

            def _attrs_ok(attrs):
                if skip_hidden and (attrs & FILE_ATTRIBUTE_HIDDEN):
                    return False
                if skip_system and (attrs & FILE_ATTRIBUTE_SYSTEM):
                    return False
                return True

            def worker():
                local = []
                while not stop.is_set():
                    with pending_lock:
                        if work.empty() and pending[0] == 0:
                            break
                        try:
                            dirpath = work.get_nowait()
                        except queue.Empty:
                            continue

                    try:
                        with os.scandir(dirpath) as it:
                            for entry in it:
                                if stop.is_set():
                                    break
                                name = entry.name
                                try:
                                    st = entry.stat(follow_symlinks=False)
                                except OSError:
                                    continue
                                attrs = getattr(st, 'st_file_attributes', 0)

                                if entry.is_dir(follow_symlinks=False):
                                    # 跳过重解析点（junction/符号链接）避免循环
                                    if attrs & FILE_ATTRIBUTE_REPARSE_POINT:
                                        continue
                                    if name.lower() in exclude or name.startswith('$'):
                                        continue
                                    if not _attrs_ok(attrs):
                                        continue
                                    if include_dirs:
                                        local.append(FileIndex(
                                            name, entry.path, 0,
                                            st.st_mtime, '', 'folders', True))
                                    with pending_lock:
                                        pending[0] += 1
                                    work.put(entry.path)
                                else:
                                    if skip_hidden and (attrs & FILE_ATTRIBUTE_HIDDEN):
                                        continue
                                    ext = os.path.splitext(name)[1].lower()
                                    local.append(FileIndex(
                                        name, entry.path, st.st_size,
                                        st.st_mtime, ext,
                                        get_file_category(ext), False))
                    except OSError:
                        pass

                    with pending_lock:
                        pending[0] -= 1

                    if len(local) >= 4000:
                        with found_lock:
                            found.extend(local)
                            counter[0] += len(local)
                        self._file_count = counter[0]
                        self._status = f"正在扫描... 已找到 {counter[0]:,} 个文件"
                        local = []

                if local:
                    with found_lock:
                        found.extend(local)
                        counter[0] += len(local)
                    self._file_count = counter[0]

            threads = [threading.Thread(target=worker, daemon=True)
                       for _ in range(SCAN_WORKERS)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            with self._lock:
                self.files = found
                self._file_count = len(found)

            self._progress = 100
            elapsed = time.time() - t0
            self._index_time = elapsed

            if stop.is_set():
                self._status = f"索引已停止（找到 {len(found):,} 个文件）"
                return

            self.save_cache()
            self._status = (f"索引完成：{len(found):,} 个文件，"
                            f"用时 {elapsed:.1f} 秒")
            self._compute_counts_async()

        except Exception as e:
            self._status = f"索引失败: {e}"
        finally:
            self._indexing = False

    # ---------- 统计 ----------
    def _compute_counts_async(self):
        def run():
            counts = {}
            with self._lock:
                snapshot = self.files
            for f in snapshot:
                counts[f.category] = counts.get(f.category, 0) + 1
            self.category_counts = counts
        threading.Thread(target=run, daemon=True).start()

    def get_all(self):
        with self._lock:
            return self.files

    def get_count(self):
        with self._lock:
            return len(self.files)
