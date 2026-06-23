"""Reference solution for fizzbuzz task."""


def fizzbuzz(n):
    """Return a list of values for 1..n with FizzBuzz rules."""
    out = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            out.append("FizzBuzz")
        elif i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(i)
    return out
