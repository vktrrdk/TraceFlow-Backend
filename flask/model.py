from pydantic import BaseModel


class NextflowRunToken(BaseModel):
    run_identifier_token: str

    def to_bson(self):
        data = self.dict(by_alias=True, exclude_none=True)
        #if data["_id"] is None:
        #    data.pop("_id")
        return data


class NextflowRun(BaseModel):
    run_token: NextflowRunToken
    name: str
    def to_bson(self):
        data = self.dict(by_alias=True, exclude_none=True)
        return data


class NextflowUser(BaseModel):
    identifier_token: str
    run_tokens: list[NextflowRunToken]
    def to_bson(self):
        data = self.dict(by_alias=True, exclude_none=True)
        #if data["_id"] is None:
        #    data.pop("_id")
        return data