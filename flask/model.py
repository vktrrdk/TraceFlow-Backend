from pydantic import BaseModel


class NextflowUser(BaseModel):
    identifier_token: str

    def to_bson(self):
        data = self.dict(by_alias=True, exclude_none=True)
        #if data["_id"] is None:
        #    data.pop("_id")
        return data


class NextflowRunToken(BaseModel):
    run_identifier_token: str

    def to_bson(self):
        data = self.dict(by_alias=True, exclude_none=True)
        #if data["_id"] is None:
        #    data.pop("_id")
        return data
