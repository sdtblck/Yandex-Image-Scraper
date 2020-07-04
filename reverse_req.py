import pyimgur
import os


path = '/Users/sidblack/Desktop/index7.png'

def upload_image(image_path='', client_id=""):
    """
    Uploads an image to imgur.

    :param client: client key for imgur API
    :param image_path: path to image on computer

    """

    im = pyimgur.Imgur(client_id)
    title = os.path.split(image_path)[1][:-4]
    print(f'Uploading {image_path}...')
    #title = txt between last / and .jpg/.png
    uploaded_image = im.upload_image(path=image_path, title=title)
    print('Done\n')
    print(uploaded_image.link)

    return uploaded_image.link

