from PIL import Image
 # Optionally, you may specify the icon sizes you want
icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (255, 255),(512,512),(1024,1024)]

# Otherwise, the default is 48x48 pixels

def convert_png_to_ico(image_filename, sizes):
    img = Image.open(image_filename)
    img.save('icon.ico', sizes=sizes, format="ICO",quality=90)

convert_png_to_ico('Logo.png',icon_sizes)
