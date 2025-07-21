class RestaurantService:
    def __init__(self):
        pass
    
    async def handle_reservation_request(self, db, user_input: str, call_sid: str):
        return "Thank you for your reservation request!", True
