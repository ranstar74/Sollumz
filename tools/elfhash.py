def generate(text):
    # https://github.com/dexyfex/CodeWalker/blob/8998b8c808a8ac234f32a2928108ac38874add69/CodeWalker.Core/GameFiles/Resources/Drawable.cs#L2278
    
    bts = text.upper()
    hash = 0
    for i in range(len(bts)):
        
        hash = (hash << 4) + ord(bts[i])

        x = hash & 0xF0000000
        if x:
            hash ^= (x >> 24)
        
        hash &= ~x
    return hash % 0xFE8F + 0x170
