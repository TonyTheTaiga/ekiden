from tortoise import fields
from tortoise.models import Model


class Identity(Model):
    id: int = fields.IntField(pk=True)
    name: str = fields.TextField()
    about: str = fields.TextField()
    picture: str = fields.TextField()
    pubkey: str = fields.TextField()

    def __str__(self) -> str:
        return self.id


class Event(Model):
    id: str = fields.TextField(pk=True)
    identity = fields.ForeignKeyField("models.Identity", related_name="events")

    kind = fields.IntField()
    content: str = fields.TextField()
    created_at = fields.IntField()
    tags = fields.JSONField()
    pubkey: str = fields.TextField()
    sig: str = fields.TextField()

    def __str__(self) -> str:
        return self.id
