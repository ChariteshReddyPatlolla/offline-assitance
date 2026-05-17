from shared.database import engine, Base
from shared.models import User, Session, Message

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Done.")
