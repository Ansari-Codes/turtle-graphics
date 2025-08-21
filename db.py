import asyncpg

DB_CONFIG = {
    'user': 'postgres',
    'password': 'postgres@app',
    'database': 'users',
    'host': 'localhost',
    'port': 7864,
}

async def get_db_conn():
    return await asyncpg.connect(**DB_CONFIG)
