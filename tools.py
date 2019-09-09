def remap(x, oMin, oMax, nMin, nMax ):

    #range check
    if oMin == oMax:
        #print "Warning: Zero input range"
        return None

    if nMin == nMax:
        #print "Warning: Zero output range"
        return None

    #check reversed input range
    reverseInput = False
    oldMin = min( oMin, oMax )
    oldMax = max( oMin, oMax )
    if not oldMin == oMin:
        reverseInput = True

    #check reversed output range
    reverseOutput = False
    newMin = min( nMin, nMax )
    newMax = max( nMin, nMax )
    if not newMin == nMin :
        reverseOutput = True

    portion = (x-oldMin)*(newMax-newMin)/(oldMax-oldMin)
    if reverseInput:
        portion = (oldMax-x)*(newMax-newMin)/(oldMax-oldMin)

    result = portion + newMin
    if reverseOutput:
        result = newMax - portion

    return result



notes = ("C","C#","D","D#","E","F","F#","G","G#","A","A#","B")
for x in range(0,128):
	print(  x, hex(x), notes[x%12], int(x/12) )

print ( int(remap(56, 48, 72, 0, 127) ))