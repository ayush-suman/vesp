from vespwood import schema
from vespwood.prompt_structure._format_object import to_format_object
from dataclasses import dataclass

@schema
@dataclass
class ChangeReview:
    analysis: str
    change_required: bool


def test_to_format_object():
    data = { "analysis": "abc", "change_required": False }
    change_review = ChangeReview.load(data)
    obj = to_format_object(change_review)
    assert obj["change_required"] == False


def test_normalized():
    data = { "analysis": "abc", "change_required": False }
    change_review = ChangeReview.load(data)
    obj = to_format_object(change_review)
    assert obj["change_required"] == False
    change_review: ChangeReview = obj.normalized
    assert change_review.change_required == False


