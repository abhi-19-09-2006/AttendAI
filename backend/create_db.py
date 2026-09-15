import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect('postgresql://attendai:attendai_dev_password@localhost:5432/postgres')
    try:
        await conn.execute('DROP DATABASE IF EXISTS attendai_test')
    except Exception as e:
        print(f"Drop error: {e}")
    try:
        await conn.execute('CREATE DATABASE attendai_test')
    except Exception as e:
        print(f"Create error: {e}")
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
