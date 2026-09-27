def int_to_english(n: int) -> str:
    """Convert a positive integer (≤999 trillion) to English words without recursion."""
    try:
        if not isinstance(n, int) or n < 0 or n > 999_000_000_000_000:
            return "Error: input must be an integer between 0 and 999 trillion."
        if n == 0:
            return "zero"
        ones = ["","one","two","three","four","five","six","seven","eight","nine"]
        teens = ["ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen","nineteen"]
        tens = ["","", "twenty","thirty","forty","fifty","sixty","seventy","eighty","ninety"]
        scales = ["","thousand","million","billion","trillion"]
        words = []
        i = 0
        while n > 0:
            chunk = n % 1000
            if chunk:
                chunk_words = []
                h = chunk // 100
                t = chunk % 100
                if h:
                    chunk_words.append(ones[h])
                    chunk_words.append("hundred")
                if t < 10:
                    if t:
                        chunk_words.append(ones[t])
                elif t < 20:
                    chunk_words.append(teens[t-10])
                else:
                    chunk_words.append(tens[t//10])
                    if t % 10:
                        chunk_words.append(ones[t%10])
                if scales[i]:
                    chunk_words.append(scales[i])
                words = chunk_words + words
            n //= 1000
            i += 1
        return " ".join([w for w in words if w])
    except Exception as e:
        return f"Error: {e}"