from time import sleep
from sys import exit
from pathlib import Path
from string import punctuation
from mimetypes import guess_extension
from urllib.request import urlretrieve
from urllib.parse import urlparse, urljoin
from urllib.error import HTTPError
from os.path import splitext
from os import remove
from gooey import Gooey, GooeyParser
from requests import get
from requests_html import HTMLSession
from cairosvg import svg2png
from PIL import Image


@Gooey(
    program_name="Generic Image Downloader",
    program_description="Downloads and resizes images from any webpage",
)
def main():
    parser = GooeyParser()

    parser.add_argument(
        "OutputDirectory",
        help="Select the directory to save images in",
        widget="DirChooser",
    )

    parser.add_argument("URL", help="Web address to download images from")

    parser.add_argument("CSS_Selectors", help="CSS selectors for the images")

    parser.add_argument(
        "Naming_Source",
        widget='Dropdown',
        choices=['Alt text', 'Original filename'],
        help="Save image using alt text or original filename",
    )

    args = parser.parse_args()

    WORKING_URL = args.URL
    OUTPUT_DIRECTORY = Path(args.OutputDirectory)
    CSS_SELECTORS = args.CSS_Selectors
    NAMING_SOURCE = args.Naming_Source

    def create_directory():
        Path(OUTPUT_DIRECTORY).mkdir(parents=True, exist_ok=True)

    def cleanup_name(image_name):
        image_name = image_name.lower()
        remove_punctuation = str.maketrans('', '', punctuation)
        image_name = image_name.translate(remove_punctuation)
        image_name = image_name.replace("'", "")
        image_name = image_name.replace("  ", "_")
        image_name = image_name.replace(" ", "_")
        return image_name

    def get_base_url():
        session = HTMLSession()
        r = session.get(WORKING_URL)
        try:
            base_url = r.html.find("base", first=True).attrs["href"]
            return base_url

        except AttributeError:
            return WORKING_URL

    def active_blocking_message():
        print(
            "It seems like the website you're trying to download images from is actively blocking programs like this from working. Try downloading the image manually.\n",
            flush=True,
        )
        exit(1)

    def get_file_format(image_url):
        image_formats = [
            ".jpg", ".jpeg", ".jpe", ".gif", ".png", ".tga", ".tiff", ".webp"
        ]
        path = urlparse(image_url).path
        extension = splitext(path)[1]
        if extension in image_formats:
            return extension

        else:
            base = get_base_url()
            image_url = urljoin(base, image_url, allow_fragments=False)
            response = get(image_url)
            content_type = response.headers['content-type']
            extension = guess_extension(content_type)
            return extension

    def get_file_name(image_url):
        "Gets filename disregarding alt text"
        path = urlparse(image_url).path
        file_name = splitext(path)[0].split(sep="/")[-1]
        return file_name

    def get_image_links():
        print("Getting image links...\n", flush=True)
        session = HTMLSession()
        r = session.get(WORKING_URL)
        images = r.html.find(CSS_SELECTORS)
        return images

    # def get_image_links_javascript():
    #     session = HTMLSession()
    #     r = session.get(WORKING_URL)
    #     r.html.render()
    #     images = r.html.find(CSS_SELECTORS)

    #     # images = ""
    #     return images

    def is_absolute(image_url):
        return bool(urlparse(image_url).netloc)

    def download_images():
        path_all_downloaded_files = []
        images = get_image_links()

        # if len(images) < 1:
        #     images = get_image_links_javascript()

        if len(images) < 1:
            print("No images found. Try downloading manually.\n", flush=True)
            exit(1)

        print("Downloading images...\n", flush=True)
        base = get_base_url()

        for image in images:
            try:
                image_url = image.attrs["src"]
            except KeyError:
                active_blocking_message()

            if is_absolute(image_url) is False:
                image_url = urljoin(base, image_url, allow_fragments=False)

            if NAMING_SOURCE == "Alt text":
                try:
                    image_name = image.attrs["alt"]
                except KeyError:
                    print(
                        "No Alt text available. Using original filename instead.\n",
                        flush=True,
                    )
                    image_name = get_file_name(image_url)

            elif NAMING_SOURCE == "Original filename":
                image_name = get_file_name(image_url)

            image_format = get_file_format(image_url)

            image_name = cleanup_name(image_name)

            image_save_name = image_name + image_format

            full_save_path = OUTPUT_DIRECTORY / image_save_name

            path_all_downloaded_files.append(full_save_path)

            try:
                urlretrieve(image_url, OUTPUT_DIRECTORY / image_save_name)

            except HTTPError:
                active_blocking_message()

        return path_all_downloaded_files

    def resize_images(path_all_downloaded_files):
        print("Resizing images...\n", flush=True)
        image_formats = [
            ".jpg", ".jpeg", ".jpe", ".gif", ".png", ".tga", ".tiff", ".webp"
        ]

        OUTPUT_DIRECTORY_Path = Path(OUTPUT_DIRECTORY)

        svgs = OUTPUT_DIRECTORY_Path.glob('*.svg')

        for svg in svgs:
            filename = str(svg.stem)
            output_filename = str(filename) + ".png"
            svg2png(url=str(svg), write_to=str(output_filename))
            path_all_downloaded_files.append(Path(output_filename))

        for img_file in path_all_downloaded_files:

            if img_file.is_file() and img_file.suffix in image_formats:
                img = Image.open(img_file)
                longest_dimension = max(img.size)

                if longest_dimension < 500:
                    size = (longest_dimension, longest_dimension)
                else:
                    size = (500, 500)

                img.thumbnail(size, Image.ANTIALIAS)
                background = Image.new('RGBA', size, (255, 255, 255, 0))
                background.paste(
                    img,
                    (
                        int((size[0] - img.size[0]) / 2),
                        int((size[1] - img.size[1]) / 2),
                    ),
                )

                resized_image_save_name = str(img_file.stem) + ".png"

                background.save(OUTPUT_DIRECTORY_Path / resized_image_save_name)

                file_format = img_file.suffix
                if file_format != ".png":
                    remove(img_file)

                svgs = OUTPUT_DIRECTORY_Path.glob('*.svg')
                for svg in svgs:
                    remove(svg)

    create_directory()
    path_all_downloaded_files = download_images()
    resize_images(path_all_downloaded_files)
    print("Finished!\n", flush=True)


main()
