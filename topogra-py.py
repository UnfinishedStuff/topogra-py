"""
A set of function for taking publickl-available topography data and drawing a
"heatmap"-style image with it.  This was designed for use with the OSNI 50m DTM
data for Northern Ireland available at:
https://www.opendatani.gov.uk/dataset/osni-open-data-50m-dtm
These functions currently do not handle below-sea level data, mostly because
NI is, at most, 1-2m below sea level.  I may alter this in the future
if I find more interesting datasets which would make use of this feature.

"""
from PIL import Image


inputFile = "50m_DTM.csv"
borderThickness = 3
saveLocation = "output.bmp"


"""
A function for remapping X/Y coordinates.
The grid coordinates of the data don't start at 0, so they need remapped to
make them easier to plot.  This also means that you can use the maximum X/Y
values as the height/width of the image to generate.  They also need to be
remapped to be contiguous, e.g. 50m DTM data is 25m, 75m, 125m, so process to
be 1,2,3 etc.
"""
def remapData (dataList, resolution, offset):
    minValue = min(dataList)

    dataList = dataList

    divisor = (minValue - offset) / resolution
    
    for x in range (0, len(dataList)):
        dataList[x] = int(((dataList[x] - offset) / resolution) - divisor)

    return dataList


"""
A function for kludgily converting heights into colour gradients.  ranges from
blue (low) to red/violet (high).  "value" is the height value (i.e. the Z) from
the DTM dataset, scale is a multiplier so that the heights are stretched across
the colour scale.  There are 6 "stages" of the colour gradient, each 0-255,
giving a total of 1530 colours.  Divide the maximum height in the dataset by
this
"""
def getColour(value, scale, heightFloor = 1):

    r,g,b = 0,0,0

    blocks = int((value * scale) / 255)
    remainder = int(value * scale) % 255

    # Fixed red, increasing blue
    if blocks == 5:
        b = remainder
        g = 0
        r = 255
    # Fixed red, decreasing green
    elif blocks == 4:
        b = 0
        g = 255 - remainder
        r = 255
    # Fixed Green, increasing red
    elif blocks == 3:
        b = 0
        g = 255
        r = remainder
    # Fixed Green, decreasing blue
    elif blocks == 2:
        b = 255 - remainder
        g = 255
        r = 0
    # Fixed blue, increasing gren
    elif blocks == 1:
        b = 255
        g = remainder
        r = 0
    # Increasing blue
    elif blocks == 0:
        b = remainder
        g = 0
        r = 0

    # Set a floor for low-height areas
    
    if (r+g+b) < heightFloor:
        b = heightFloor
    
    
    return((r,g,b))

"""
A highly clunky function to draw a white border around the landmass.  Pass it
a PIL Image object.  This creates a fresh copy called withBorder.  Each pixel
in the original image is checked, and if the RGB value = 0,0,0 (no height data)
then the pixels above, below, left and right are checked.  If any of those
have RGB values which are NOT 0 (i.e. contain height data) then the original
pixel is considered a "border" pixel.  To prevent newly written border pixels
counting as pixels with height on checking subsequent pixels, the pixel at the
corresponding X/Y coordinates in the withBorder image is set to white, not the
pixel in the original image.
"""
def border(image, rounds, border_colour=(255,255,255)):

    reference = image
    withBorder = image.copy()

    for rnd in range (0, rounds):

        print("Applying border, round " + str(rnd) + "...")
        
        for x in range (0, reference.width):
            for y in range (0, reference.height):

                pixel = reference.getpixel((x, y))
                
                if pixel == (0,0,0):
                    try:
                        up = reference.getpixel((x, y-1))
                    except IndexError:
                        up = (0,0,0)
                    try:
                        down = reference.getpixel((x, y+1))
                    except IndexError:
                        down = (0,0,0)
                    try:
                        left = reference.getpixel((x-1, y))
                    except IndexError:
                        left = (0,0,0)
                    try:
                        right = reference.getpixel((x+1, y))
                    except IndexError:
                        right = (0,0,0)

                    if (up != (0,0,0)) or (down != (0,0,0)) or (left != (0,0,0)) or (right != (0,0,0)):
                        withBorder.putpixel((x, y), (border_colour))

        reference = withBorder.copy()            

    return withBorder

"""
A function to draw the masic map.  Takes the file location of a dataset as an
input.  Resolution is the resolution of the dataset (50m for the OSNI 50m DMT
data this program was designed for).  coordinateOffset is a value which is
subtracted from X/Y coordinates to get them zeroed: the 50m data does not run as
0,50,100,150, it runs as 25, 75, 125, 175.  To make plotting the data easier
the X/Y coordinates are boiled down from their native state to 0,1,2,3, etc.,
and so this coordinateOffset is used to enable this.
"""
def drawMap(dataFile, resolution=50, coordinateOffset=25):

    print("Reading file...")
    # Open the file containing the DTM data
    with open (dataFile, "r") as file:
        lines = file.readlines()
    # First line has header information, get rid of it
    del lines[0]

    # Initialise three list to hold processed data from the DTM file
    xData = []
    yData = []
    zData = []

    print("Pre-processing the data...")
    # For each line in the DTM file
    for line in lines:
        # get rid of the newline char at the end of the line, and split into X/Y/Z
        #rawline = line[0:-2].split(",")
        rawline = line[0:-2]
        rawline = rawline.split(",")
    
        # Append the values to the appropriate list
        xData.append(int(rawline[0]))
        yData.append(int(rawline[1]))
    
        # Some of the Z values are slightly negative (0.5-1.5m), zero these to avoid
        # issues with the colour gradient
        height = float(rawline[2])
        if height < 0:
            zData.append(0)
        else:
            zData.append(int(height))

    # Remap the data (see the remapData function for a description)
    print("Remapping X..")
    xData = remapData(xData, resolution, coordinateOffset)
    print("Remapping Y...")
    yData = remapData(yData, resolution, coordinateOffset)

    # Get the maximum X and Y values, these are essentially the width and height of
    # the map to draw
    xMax = max(xData)
    yMax = max(yData)

    # Create an image object for the map
    img = Image.new("RGB", (xMax + 1, yMax + 1))

    print("Drawing the map...")
    # For every data point in the DTM data:
    for x in range (0, len(zData)):
        # At the corresponding X and Y coordinates in the image set the RGB
        # values of that pixel to a colour which scales to the height
        img.putpixel((int(xData[x]), int(yData[x])), getColour(zData[x], 1.8))

    return img

# Draw the height map
img = drawMap(inputFile)
# Flip the image (not sure why the data is mirrored
img = img.transpose(Image.FLIP_TOP_BOTTOM)
# Add three rounds of a white border
img = border(img, borderThickness)
print("Done!")
# Show the image
img.save(saveLocation)

