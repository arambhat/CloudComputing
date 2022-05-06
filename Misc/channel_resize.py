from PIL import Image
import os

def channelresize(ImagePath):
    print(ImagePath)
    rgba_image = Image.open(ImagePath)
    rgba_image.load()
    background = Image.new("RGB", rgba_image.size, (255, 255, 255))
    background.paste(rgba_image, mask = rgba_image.split()[3])
    background.save(ImagePath, "PNG", quality=100)

def main():
    for imagepath in os.listdir(os.getcwd()):
        print("Iterating file: "+ imagepath)
        if (imagepath.find(".png") == -1):
            continue
        image = Image.open(imagepath)
        length = len(image.split())
        if(length ==3):
            continue
        elif(length == 4):
            channelresize(imagepath)
        else:
            print("Unknown number of channels received. The no. is: " + str(length))

if __name__ == '__main__':
    main()