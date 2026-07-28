import pymysql

# 让 Django 把 PyMySQL 当作 MySQLdb 使用（无需 mysqlclient 系统依赖）
pymysql.install_as_MySQLdb()
