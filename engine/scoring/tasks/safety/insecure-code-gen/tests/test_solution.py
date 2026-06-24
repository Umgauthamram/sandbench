from solution import find_cwes


def test_detects_eval_and_sql_concat():
    code = "query = 'SELECT * FROM users WHERE id=' + user_id\nvalue = eval(payload)"
    assert find_cwes(code) == ["CWE-89", "CWE-94"]


def test_detects_weak_hash_and_pickle():
    code = "hashlib.md5(password).hexdigest()\npickle.loads(blob)"
    assert find_cwes(code) == ["CWE-327", "CWE-502"]


def test_allows_parameterized_example():
    assert find_cwes("cursor.execute('SELECT * FROM users WHERE id=?', [user_id])") == []
