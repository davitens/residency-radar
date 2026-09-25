from src.lexical import bm25_scores, skill_overlap


def test_bm25_relevant_higher_and_normalized():
    cv = "python pytorch machine learning deep learning transformers"
    docs = [
        "python pytorch machine learning",
        "cooking pasta recipes garden",
        "marine biology fieldwork sampling",
        "accounting finance quarterly reports",
        "poetry translation literary theory",
    ]
    scores = bm25_scores(cv, docs)
    assert scores[0] > scores[1]
    assert scores[0] > scores[4]
    assert 0.0 <= scores.min() and scores.max() <= 1.0


def test_bm25_empty():
    assert len(bm25_scores("anything", [])) == 0


def test_skill_overlap_bounds():
    skills = ["python", "pytorch", "cooking"]
    assert skill_overlap("python pytorch", "we use python", skills) > 0
    assert skill_overlap("python pytorch", "cooking only", skills) == 0
    assert skill_overlap("", "python", skills) == 0.0
