from app import mongo

class FirefighterModel:
    @staticmethod
    def insert_data(data):
        """Insert new firefighter deployment data into MongoDB."""
        return mongo.db.firefighters.insert_one(data)

    @staticmethod
    def get_all_data():
        """Retrieve all deployment records from MongoDB."""
        return list(mongo.db.firefighters.find({}, {"_id": 0}))