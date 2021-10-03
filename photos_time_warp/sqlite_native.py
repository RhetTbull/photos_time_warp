""" Provide access to native OS sqlite library (bypasses python's sqlite3) """

# Why would you want to do this?
# python's sqlite3 refuses to open a database that's got a lock on it while the OS sqlite library happily opens it
# This is a hack to get around that. Use at your own risk!

# Reference:
# https://gist.github.com/michalc/a3147997e21665896836e0f4157975cb
# https://stackoverflow.com/a/68876046/1319998, which is itself inspired by https://stackoverflow.com/a/68814418/1319998

from collections import namedtuple
from contextlib import contextmanager
from ctypes import byref, c_char_p, c_double, c_int, c_int64, c_void_p, cdll, string_at
from sys import platform


def query(db_file, sql, params=()):
    libsqlite3 = cdll.LoadLibrary(
        {"linux": "libsqlite3.so", "darwin": "libsqlite3.dylib"}[platform]
    )
    libsqlite3.sqlite3_errstr.restype = c_char_p
    libsqlite3.sqlite3_errmsg.restype = c_char_p
    libsqlite3.sqlite3_column_name.restype = c_char_p
    libsqlite3.sqlite3_column_double.restype = c_double
    libsqlite3.sqlite3_column_int64.restype = c_int64
    libsqlite3.sqlite3_column_blob.restype = c_void_p
    libsqlite3.sqlite3_column_bytes.restype = c_int64
    SQLITE_ROW = 100
    SQLITE_DONE = 101
    SQLITE_TRANSIENT = -1
    SQLITE_OPEN_READWRITE = 0x00000002

    bind = {
        type(0): libsqlite3.sqlite3_bind_int64,
        type(0.0): libsqlite3.sqlite3_bind_double,
        type(""): lambda pp_stmt, i, value: libsqlite3.sqlite3_bind_text(
            pp_stmt,
            i,
            value.encode("utf-8"),
            len(value.encode("utf-8")),
            SQLITE_TRANSIENT,
        ),
        type(b""): lambda pp_stmt, i, value: libsqlite3.sqlite3_bind_blob(
            pp_stmt, i, value, len(value), SQLITE_TRANSIENT
        ),
        type(None): lambda pp_stmt, i, _: libsqlite3.sqlite3_bind_null(pp_stmt, i),
    }

    extract = {
        1: libsqlite3.sqlite3_column_int64,
        2: libsqlite3.sqlite3_column_double,
        3: lambda pp_stmt, i: string_at(
            libsqlite3.sqlite3_column_blob(pp_stmt, i),
            libsqlite3.sqlite3_column_bytes(pp_stmt, i),
        ).decode(),
        4: lambda pp_stmt, i: string_at(
            libsqlite3.sqlite3_column_blob(pp_stmt, i),
            libsqlite3.sqlite3_column_bytes(pp_stmt, i),
        ),
        5: lambda pp_stmt, i: None,
    }

    def run(func, *args):
        res = func(*args)
        if res != 0:
            raise Exception(libsqlite3.sqlite3_errstr(res).decode())

    def run_with_db(db, func, *args):
        if func(*args) != 0:
            raise Exception(libsqlite3.sqlite3_errmsg(db).decode())

    @contextmanager
    def get_db(db_file):
        db = c_void_p()
        run(
            libsqlite3.sqlite3_open_v2,
            db_file.encode(),
            byref(db),
            SQLITE_OPEN_READWRITE,
            None,
        )
        try:
            yield db
        finally:
            run_with_db(db, libsqlite3.sqlite3_close, db)

    @contextmanager
    def get_pp_stmt(db, sql):
        pp_stmt = c_void_p()
        run_with_db(
            db,
            libsqlite3.sqlite3_prepare_v3,
            db,
            sql.encode(),
            -1,
            0,
            byref(pp_stmt),
            None,
        )
        try:
            yield pp_stmt
        finally:
            run_with_db(db, libsqlite3.sqlite3_finalize, pp_stmt)

    with get_db(db_file) as db, get_pp_stmt(db, sql) as pp_stmt:

        for i, param in enumerate(params):
            run_with_db(db, bind[type(param)], pp_stmt, i + 1, param)

        row_constructor = namedtuple(
            "Row",
            (
                libsqlite3.sqlite3_column_name(pp_stmt, i).decode()
                for i in range(0, libsqlite3.sqlite3_column_count(pp_stmt))
            ),
        )

        while True:
            res = libsqlite3.sqlite3_step(pp_stmt)
            if res == SQLITE_DONE:
                break
            if res != SQLITE_ROW:
                raise Exception(libsqlite3.sqlite3_errstr(res).decode())

            yield row_constructor(
                *(
                    extract[libsqlite3.sqlite3_column_type(pp_stmt, i)](pp_stmt, i)
                    for i in range(0, len(row_constructor._fields))
                )
            )


def execute(db_file, sql):
    """run a sql statement that might update the db"""

    # this is needed because if the generator returned by query isn't exhausted, the SQL statement doesn't actually get executed

    results = query(db_file, sql)
    rows = []
    try:
        for row in results:
            rows.append(row)
    except StopIteration:
        pass
    return rows or None
