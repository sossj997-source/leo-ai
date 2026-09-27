def number_to_words(num) -> str:
    """Convert an int or float to its English words representation."""
    try:
        units = ["zero","one","two","three","four","five","six","seven","eight","nine","ten",
                 "eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen",
                 "eighteen","nineteen"]
        tens = ["","","twenty","thirty","forty","fifty","sixty","seventy","eighty","ninety"]
        scales = ["","thousand","million","billion","trillion","quadrillion","quintillion"]
        def _convert_int(n):
            if n < 0:
                return "minus " + _convert_int(-n)
            if n < 20:
                return units[n]
            if n < 100:
                return tens[n//10] + ("" if n%10==0 else " " + units[n%10])
            for i,scale in enumerate(scales[1:],1):
                p = 1000**i
                if n < p*1000:
                    high, low = divmod(n, p)
                    return _convert_int(high) + " " + scale + ("" if low==0 else " " + _convert_int(low))
            return str(n)
        def _digit_word(d): return units[int(d)]
        if isinstance(num, int):
            return _convert_int(num)
        if isinstance(num, float):
            int_part = int(num)
            frac_str = str(num).split('.')[1].rstrip('0')
            words = _convert_int(int_part)
            if not frac_str:
                return words
            return words + " point " + " ".join(_digit_word(d) for d in frac_str)
        return "Unsupported type"
    except Exception as e:
        return f"Error: {e}"