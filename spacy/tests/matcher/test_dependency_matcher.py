import pytest
import pickle
import re
import copy
from mock import Mock
from spacy.matcher import DependencyMatcher
from ..util import get_doc


@pytest.fixture
def doc(en_vocab):
    text = "The quick brown fox jumped over the lazy fox"
    heads = [3, 2, 1, 1, 0, -1, 2, 1, -3]
    deps = ["det", "amod", "amod", "nsubj", "ROOT", "prep", "pobj", "det", "amod"]
    doc = get_doc(en_vocab, text.split(), heads=heads, deps=deps)
    return doc


@pytest.fixture
def patterns(en_vocab):
    def is_brown_yellow(text):
        return bool(re.compile(r"brown|yellow").match(text))

    IS_BROWN_YELLOW = en_vocab.add_flag(is_brown_yellow)

    pattern1 = [
        {"RIGHT_ID": "fox", "RIGHT_ATTRS": {"ORTH": "fox"}},
        {
            "LEFT_ID": "fox",
            "REL_OP": ">",
            "RIGHT_ID": "q",
            "RIGHT_ATTRS": {"ORTH": "quick", "DEP": "amod"},
        },
        {
            "LEFT_ID": "fox",
            "REL_OP": ">",
            "RIGHT_ID": "r",
            "RIGHT_ATTRS": {IS_BROWN_YELLOW: True},
        },
    ]

    pattern2 = [
        {"RIGHT_ID": "jumped", "RIGHT_ATTRS": {"ORTH": "jumped"}},
        {
            "LEFT_ID": "jumped",
            "REL_OP": ">",
            "RIGHT_ID": "fox1",
            "RIGHT_ATTRS": {"ORTH": "fox"},
        },
        {
            "LEFT_ID": "jumped",
            "REL_OP": ".",
            "RIGHT_ID": "over",
            "RIGHT_ATTRS": {"ORTH": "over"},
        },
    ]

    pattern3 = [
        {"RIGHT_ID": "jumped", "RIGHT_ATTRS": {"ORTH": "jumped"}},
        {
            "LEFT_ID": "jumped",
            "REL_OP": ">",
            "RIGHT_ID": "fox",
            "RIGHT_ATTRS": {"ORTH": "fox"},
        },
        {
            "LEFT_ID": "fox",
            "REL_OP": ">>",
            "RIGHT_ID": "r",
            "RIGHT_ATTRS": {"ORTH": "brown"},
        },
    ]

    pattern4 = [
        {"RIGHT_ID": "jumped", "RIGHT_ATTRS": {"ORTH": "jumped"}},
        {
            "LEFT_ID": "jumped",
            "REL_OP": ">",
            "RIGHT_ID": "fox",
            "RIGHT_ATTRS": {"ORTH": "fox"},
        },
    ]

    pattern5 = [
        {"RIGHT_ID": "jumped", "RIGHT_ATTRS": {"ORTH": "jumped"}},
        {
            "LEFT_ID": "jumped",
            "REL_OP": ">>",
            "RIGHT_ID": "fox",
            "RIGHT_ATTRS": {"ORTH": "fox"},
        },
    ]

    return [pattern1, pattern2, pattern3, pattern4, pattern5]


@pytest.fixture
def dependency_matcher(en_vocab, patterns, doc):
    matcher = DependencyMatcher(en_vocab)
    mock = Mock()
    for i in range(1, len(patterns) + 1):
        if i == 1:
            matcher.add("pattern1", [patterns[0]], on_match=mock)
        else:
            matcher.add("pattern" + str(i), [patterns[i - 1]])

    return matcher


def test_dependency_matcher(dependency_matcher, doc, patterns):
    assert len(dependency_matcher) == 5
    assert "pattern3" in dependency_matcher
    assert dependency_matcher.get("pattern3") == (None, [patterns[2]])
    matches = dependency_matcher(doc)
    assert len(matches) == 6
    assert matches[0][1] == [3, 1, 2]
    assert matches[1][1] == [4, 3, 5]
    assert matches[2][1] == [4, 3, 2]
    assert matches[3][1] == [4, 3]
    assert matches[4][1] == [4, 3]
    assert matches[5][1] == [4, 8]

    span = doc[0:6]
    matches = dependency_matcher(span)
    assert len(matches) == 5
    assert matches[0][1] == [3, 1, 2]
    assert matches[1][1] == [4, 3, 5]
    assert matches[2][1] == [4, 3, 2]
    assert matches[3][1] == [4, 3]
    assert matches[4][1] == [4, 3]


def test_dependency_matcher_pickle(en_vocab, patterns, doc):
    matcher = DependencyMatcher(en_vocab)
    for i in range(1, len(patterns) + 1):
        matcher.add("pattern" + str(i), [patterns[i - 1]])

    matches = matcher(doc)
    assert matches[0][1] == [3, 1, 2]
    assert matches[1][1] == [4, 3, 5]
    assert matches[2][1] == [4, 3, 2]
    assert matches[3][1] == [4, 3]
    assert matches[4][1] == [4, 3]
    assert matches[5][1] == [4, 8]

    b = pickle.dumps(matcher)
    matcher_r = pickle.loads(b)

    assert len(matcher) == len(matcher_r)
    matches = matcher_r(doc)
    assert matches[0][1] == [3, 1, 2]
    assert matches[1][1] == [4, 3, 5]
    assert matches[2][1] == [4, 3, 2]
    assert matches[3][1] == [4, 3]
    assert matches[4][1] == [4, 3]
    assert matches[5][1] == [4, 8]


def test_dependency_matcher_pattern_validation(en_vocab):
    pattern = [
        {"RIGHT_ID": "fox", "RIGHT_ATTRS": {"ORTH": "fox"}},
        {
            "LEFT_ID": "fox",
            "REL_OP": ">",
            "RIGHT_ID": "q",
            "RIGHT_ATTRS": {"ORTH": "quick", "DEP": "amod"},
        },
        {
            "LEFT_ID": "fox",
            "REL_OP": ">",
            "RIGHT_ID": "r",
            "RIGHT_ATTRS": {"ORTH": "brown"},
        },
    ]

    matcher = DependencyMatcher(en_vocab)
    # original pattern is valid
    matcher.add("FOUNDED", [pattern])
    # individual pattern not wrapped in a list
    with pytest.raises(ValueError):
        matcher.add("FOUNDED", pattern)
    # no anchor node
    with pytest.raises(ValueError):
        matcher.add("FOUNDED", [pattern[1:]])
    # required keys missing
    with pytest.raises(ValueError):
        pattern2 = copy.deepcopy(pattern)
        del pattern2[0]["RIGHT_ID"]
        matcher.add("FOUNDED", [pattern2])
    with pytest.raises(ValueError):
        pattern2 = copy.deepcopy(pattern)
        del pattern2[1]["RIGHT_ID"]
        matcher.add("FOUNDED", [pattern2])
    with pytest.raises(ValueError):
        pattern2 = copy.deepcopy(pattern)
        del pattern2[1]["RIGHT_ATTRS"]
        matcher.add("FOUNDED", [pattern2])
    with pytest.raises(ValueError):
        pattern2 = copy.deepcopy(pattern)
        del pattern2[1]["LEFT_ID"]
        matcher.add("FOUNDED", [pattern2])
    with pytest.raises(ValueError):
        pattern2 = copy.deepcopy(pattern)
        del pattern2[1]["REL_OP"]
        matcher.add("FOUNDED", [pattern2])
    # invalid operator
    with pytest.raises(ValueError):
        pattern2 = copy.deepcopy(pattern)
        pattern2[1]["REL_OP"] = "!!!"
        matcher.add("FOUNDED", [pattern2])
    # duplicate node name
    with pytest.raises(ValueError):
        pattern2 = copy.deepcopy(pattern)
        pattern2[1]["RIGHT_ID"] = "fox"
        matcher.add("FOUNDED", [pattern2])


def test_dependency_matcher_callback(en_vocab, doc):
    pattern = [
        {"RIGHT_ID": "quick", "RIGHT_ATTRS": {"ORTH": "quick"}},
    ]

    matcher = DependencyMatcher(en_vocab)
    mock = Mock()
    matcher.add("pattern", [pattern], on_match=mock)
    matches = matcher(doc)
    mock.assert_called_once_with(matcher, doc, 0, matches)

    # check that matches with and without callback are the same (#4590)
    matcher2 = DependencyMatcher(en_vocab)
    matcher2.add("pattern", [pattern])
    matches2 = matcher2(doc)
    assert matches == matches2


@pytest.mark.parametrize("op,num_matches", [(".", 8), (".*", 20), (";", 8), (";*", 20)])
def test_dependency_matcher_precedence_ops(en_vocab, op, num_matches):
    # two sentences to test that all matches are within the same sentence
    doc = get_doc(
        en_vocab,
        words=["a", "b", "c", "d", "e"] * 2,
        heads=[0, -1, -2, -3, -4] * 2,
        deps=["dep"] * 10,
    )
    match_count = 0
    for text in ["a", "b", "c", "d", "e"]:
        pattern = [
            {"RIGHT_ID": "1", "RIGHT_ATTRS": {"ORTH": text}},
            {"LEFT_ID": "1", "REL_OP": op, "RIGHT_ID": "2", "RIGHT_ATTRS": {}},
        ]
        matcher = DependencyMatcher(en_vocab)
        matcher.add("A", [pattern])
        matches = matcher(doc)
        match_count += len(matches)
        for match in matches:
            match_id, token_ids = match
            # token_ids[0] op token_ids[1]
            if op == ".":
                assert token_ids[0] == token_ids[1] - 1
            elif op == ";":
                assert token_ids[0] == token_ids[1] + 1
            elif op == ".*":
                assert token_ids[0] < token_ids[1]
            elif op == ";*":
                assert token_ids[0] > token_ids[1]
            # all tokens are within the same sentence
            assert doc[token_ids[0]].sent == doc[token_ids[1]].sent
    assert match_count == num_matches


@pytest.mark.parametrize(
    "left,right,op,num_matches",
    [
        ("fox", "jumped", "<", 1),
        ("the", "lazy", "<", 0),
        ("jumped", "jumped", "<", 0),
        ("fox", "jumped", ">", 0),
        ("fox", "lazy", ">", 1),
        ("lazy", "lazy", ">", 0),
        ("fox", "jumped", "<<", 2),
        ("jumped", "fox", "<<", 0),
        ("the", "fox", "<<", 2),
        ("fox", "jumped", ">>", 0),
        ("over", "the", ">>", 1),
        ("fox", "the", ">>", 2),
        ("fox", "jumped", ".", 1),
        ("lazy", "fox", ".", 1),
        ("the", "fox", ".", 0),
        ("the", "the", ".", 0),
        ("fox", "jumped", ";", 0),
        ("lazy", "fox", ";", 0),
        ("the", "fox", ";", 0),
        ("the", "the", ";", 0),
        ("quick", "fox", ".*", 2),
        ("the", "fox", ".*", 3),
        ("the", "the", ".*", 1),
        ("fox", "jumped", ";*", 1),
        ("quick", "fox", ";*", 0),
        ("the", "fox", ";*", 1),
        ("the", "the", ";*", 1),
        ("quick", "brown", "$+", 1),
        ("brown", "quick", "$+", 0),
        ("brown", "brown", "$+", 0),
        ("quick", "brown", "$-", 0),
        ("brown", "quick", "$-", 1),
        ("brown", "brown", "$-", 0),
        ("the", "brown", "$++", 1),
        ("brown", "the", "$++", 0),
        ("brown", "brown", "$++", 0),
        ("the", "brown", "$--", 0),
        ("brown", "the", "$--", 1),
        ("brown", "brown", "$--", 0),
    ],
)
def test_dependency_matcher_ops(en_vocab, doc, left, right, op, num_matches):
    right_id = right
    if left == right:
        right_id = right + "2"
    pattern = [
        {"RIGHT_ID": left, "RIGHT_ATTRS": {"LOWER": left}},
        {
            "LEFT_ID": left,
            "REL_OP": op,
            "RIGHT_ID": right_id,
            "RIGHT_ATTRS": {"LOWER": right},
        },
    ]

    matcher = DependencyMatcher(en_vocab)
    matcher.add("pattern", [pattern])
    matches = matcher(doc)
    assert len(matches) == num_matches