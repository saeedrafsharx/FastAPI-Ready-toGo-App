from sqlalchemy import create_engine
from main import Base, DATABASE_URL

def main():
	sync_url = DATABASE_URL.replace("+asyncpg", "")
	engine = create_engine(sync_url, echo=True)
	Base.metadata.create_all(engine)

if __name__ == "__main__":
	main()