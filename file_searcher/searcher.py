# -*- coding: utf-8 -*-
"""
搜索匹配器
支持多种匹配模式和高级搜索语法
参考 Everything 的搜索语法设计
"""
import re
import time
import threading
from fnmatch import fnmatch

from .utils import parse_size, get_file_category


class SearchQuery:
    """搜索查询解析结果"""

    def __init__(self):
        self.keywords = []  # 普通关键词（AND 关系）
        self.exclude_keywords = []  # 排除关键词
        self.extensions = []  # 指定扩展名
        self.exclude_extensions = []  # 排除扩展名
        self.categories = []  # 指定分类
        self.size_min = None  # 最小大小（字节）
        self.size_max = None  # 最大大小（字节）
        self.date_from = None  # 最早修改时间
        self.date_to = None  # 最晚修改时间
        self.match_mode = "contains"  # contains / exact / startswith / regex / wildcard
        self.case_sensitive = False
        self.path_filter = None  # 路径过滤
        self.is_dir = None  # True=只搜目录, False=只搜文件, None=全部


class Searcher:
    """高性能搜索匹配器"""

    def __init__(self, index_engine):
        self.index = index_engine
        self._searching = False
        self._stop_flag = threading.Event()
        self._results = []
        self._search_time = 0

    @property
    def is_searching(self):
        return self._searching

    def stop(self):
        self._stop_flag.set()

    def parse_query(self, query_str, match_mode="contains", case_sensitive=False):
        """
        解析搜索查询字符串
        支持语法：
        - 普通关键词：document
        - 排除关键词：!temp
        - 指定扩展名：*.pdf 或 ext:pdf
        - 指定分类：category:documents
        - 大小过滤：size:>10MB 或 size:<1GB 或 size:10MB-1GB
        - 路径过滤：path:downloads
        - 目录过滤：folder: 或 file:
        - 多个条件空格分隔（AND关系）
        """
        query = SearchQuery()
        query.match_mode = match_mode
        query.case_sensitive = case_sensitive

        if not query_str or not query_str.strip():
            return query

        parts = self._split_query(query_str.strip())

        for part in parts:
            part_lower = part.lower()

            # 排除关键词
            if part.startswith('!') and len(part) > 1:
                query.exclude_keywords.append(part[1:])
                continue

            # 扩展名模式: *.pdf
            if part.startswith('*.') and len(part) > 2:
                ext = part[1:].lower()
                query.extensions.append(ext)
                continue

            # ext: 语法
            if part_lower.startswith('ext:') and len(part) > 4:
                exts_str = part[4:]
                for e in exts_str.split(','):
                    e = e.strip().lower()
                    if e:
                        if not e.startswith('.'):
                            e = '.' + e
                        query.extensions.append(e)
                continue

            # category: 语法
            if part_lower.startswith('category:') and len(part) > 9:
                cat = part[9:].lower().strip()
                query.categories.append(cat)
                continue

            # size: 语法
            if part_lower.startswith('size:') and len(part) > 5:
                size_expr = part[5:]
                self._parse_size_filter(size_expr, query)
                continue

            # path: 语法
            if part_lower.startswith('path:') and len(part) > 5:
                query.path_filter = part[5:]
                continue

            # folder: / file: 语法
            if part_lower == 'folder:' or part_lower == 'folder':
                query.is_dir = True
                continue
            if part_lower == 'file:' or part_lower == 'file':
                query.is_dir = False
                continue

            # 普通关键词
            query.keywords.append(part)

        return query

    def _split_query(self, query_str):
        """智能分割查询字符串，处理引号包裹的短语"""
        parts = []
        current = ""
        in_quotes = False

        for ch in query_str:
            if ch == '"':
                in_quotes = not in_quotes
                continue
            if ch == ' ' and not in_quotes:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += ch

        if current:
            parts.append(current)

        return parts

    def _parse_size_filter(self, expr, query):
        """解析大小过滤表达式"""
        expr = expr.strip().lower()

        # 范围: 10MB-1GB
        if '-' in expr:
            parts = expr.split('-', 1)
            if len(parts) == 2:
                query.size_min = parse_size(parts[0])
                query.size_max = parse_size(parts[1])
                return

        # 大于: >10MB 或 >=10MB（> 为严格大于）
        if expr.startswith('>='):
            query.size_min = parse_size(expr[2:])
            return
        if expr.startswith('>'):
            query.size_min = parse_size(expr[1:]) + 1
            return

        # 小于: <1GB 或 <=1GB（< 为严格小于）
        if expr.startswith('<='):
            query.size_max = parse_size(expr[2:])
            return
        if expr.startswith('<'):
            query.size_max = parse_size(expr[1:]) - 1
            return

        # 等于: 5MB
        size = parse_size(expr)
        if size is not None:
            # 近似等于：上下浮动 10%
            query.size_min = int(size * 0.9)
            query.size_max = int(size * 1.1)

    def search(self, query_str, match_mode="contains", case_sensitive=False,
               category_filter=None, max_results=5000,
               progress_callback=None, done_callback=None):
        """
        执行搜索（异步）。连续调用时旧搜索的回调会被丢弃
        """
        self._search_id = getattr(self, "_search_id", 0) + 1
        sid = self._search_id

        self._stop_flag.clear()
        self._searching = True
        self._results = []
        self._search_time = 0

        thread = threading.Thread(
            target=self._search_worker,
            args=(query_str, match_mode, case_sensitive,
                  category_filter, max_results,
                  progress_callback, done_callback, sid),
            daemon=True
        )
        thread.start()

    def _search_worker(self, query_str, match_mode, case_sensitive,
                       category_filter, max_results,
                       progress_callback, done_callback, sid=None):
        try:
            start_time = time.time()

            # 解析查询
            query = self.parse_query(query_str, match_mode, case_sensitive)

            # 如果有分类过滤，加入查询
            if category_filter and category_filter != "all":
                query.categories.append(category_filter)

            # 获取所有文件
            all_files = self.index.get_all()
            total = len(all_files)

            # 如果没有关键词且没有过滤条件，返回全部（受max_results限制）
            if not query.keywords and not query.exclude_keywords \
                    and not query.extensions and not query.exclude_extensions \
                    and not query.categories and query.size_min is None \
                    and query.size_max is None and query.date_from is None \
                    and query.date_to is None and query.path_filter is None \
                    and query.is_dir is None:
                results = all_files[:max_results]
                elapsed = time.time() - start_time

                if sid is None or sid == self._search_id:
                    self._results = results
                    self._search_time = elapsed
                    self._searching = False
                    if done_callback:
                        try:
                            done_callback(results, elapsed)
                        except Exception:
                            pass
                return

            # 编译匹配函数
            match_fns = []
            for kw in query.keywords:
                match_fns.append(self._build_match_fn(kw, query.match_mode, query.case_sensitive))

            # 排除匹配函数
            exclude_fns = []
            for kw in query.exclude_keywords:
                exclude_fns.append(self._build_match_fn(kw, query.match_mode, query.case_sensitive))

            # 扩展名集合
            ext_set = set(e.lower() if e.startswith('.') else '.' + e.lower()
                         for e in query.extensions) if query.extensions else None
            exclude_ext_set = set(e.lower() if e.startswith('.') else '.' + e.lower()
                                 for e in query.exclude_extensions) if query.exclude_extensions else None

            # 分类集合
            cat_set = set(query.categories) if query.categories else None

            # 路径过滤
            path_filter = query.path_filter.lower() if query.path_filter else None

            results = []
            count = 0

            for f in all_files:
                if self._stop_flag.is_set():
                    break

                # 目录/文件过滤
                if query.is_dir is not None and f.is_dir != query.is_dir:
                    continue

                # 分类过滤
                if cat_set and f.category not in cat_set:
                    continue

                # 扩展名过滤
                if ext_set and f.ext not in ext_set:
                    continue
                if exclude_ext_set and f.ext in exclude_ext_set:
                    continue

                # 路径过滤
                if path_filter and path_filter not in f.path.lower():
                    continue

                # 关键词匹配（全部满足）
                matched = True
                if match_fns:
                    for fn in match_fns:
                        if not fn(f.name):
                            matched = False
                            break
                if not matched:
                    continue

                # 排除关键词（全部不满足）
                if exclude_fns:
                    excluded = False
                    for fn in exclude_fns:
                        if fn(f.name):
                            excluded = True
                            break
                    if excluded:
                        continue

                # 大小过滤
                if query.size_min is not None and f.size < query.size_min:
                    continue
                if query.size_max is not None and f.size > query.size_max:
                    continue

                results.append(f)
                count += 1

                if count >= max_results:
                    break

                # 进度回调（每1000个文件回调一次）
                if progress_callback and count % 1000 == 0:
                    try:
                        progress_callback(count, total)
                    except Exception:
                        pass

            elapsed = time.time() - start_time

            if sid is None or sid == self._search_id:
                self._results = results
                self._search_time = elapsed
                if done_callback:
                    try:
                        done_callback(results, elapsed)
                    except Exception:
                        pass

        except Exception as e:
            if done_callback and (sid is None or sid == self._search_id):
                try:
                    done_callback([], 0, str(e))
                except Exception:
                    pass
        finally:
            if sid is None or sid == self._search_id:
                self._searching = False

    def _build_match_fn(self, keyword, mode, case_sensitive):
        """构建匹配函数"""
        if not case_sensitive:
            kw = keyword.lower()
        else:
            kw = keyword

        if mode == "contains":
            if case_sensitive:
                return lambda name: kw in name
            else:
                return lambda name: kw in name.lower()

        elif mode == "exact":
            if case_sensitive:
                return lambda name: kw == name
            else:
                return lambda name: kw == name.lower()

        elif mode == "startswith":
            if case_sensitive:
                return lambda name: name.startswith(kw)
            else:
                return lambda name: name.lower().startswith(kw)

        elif mode == "endswith":
            if case_sensitive:
                return lambda name: name.endswith(kw)
            else:
                return lambda name: name.lower().endswith(kw)

        elif mode == "regex":
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(kw, flags)
                return lambda name: bool(pattern.search(name))
            except re.error:
                if case_sensitive:
                    return lambda name: kw in name
                else:
                    return lambda name: kw in name.lower()

        elif mode == "wildcard":
            if case_sensitive:
                return lambda name: fnmatch(name, kw)
            else:
                return lambda name: fnmatch(name.lower(), kw)

        # 默认包含匹配
        if case_sensitive:
            return lambda name: kw in name
        else:
            return lambda name: kw in name.lower()
