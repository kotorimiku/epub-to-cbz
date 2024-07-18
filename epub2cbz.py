import os
import xml.etree.ElementTree as ET
import zipfile
import re
import tqdm
import argparse


class epub2cbz:
    namespace: dict = {
        "ns": "urn:oasis:names:tc:opendocument:xmlns:container",
        "opf": "http://www.idpf.org/2007/opf",
        "dc": "http://purl.org/dc/elements/1.1/",
    }

    def __init__(self) -> None:
        self.zip_ref: zipfile.ZipFile
        self.opf: str
        self.image_list: list[str] = []
        self.spine: list[str] = []
        self.manifest: list[dict[str, str]] = []
        self.metadata: dict[str, str] = {}
        self.zipf: zipfile.ZipFile

    def read_epub(self, path):
        self.zip_ref = zipfile.ZipFile(path, "r")
        with self.zip_ref.open("META-INF/container.xml") as xml_file:
            tree = ET.parse(xml_file)
            self.opf = tree.find(".//ns:rootfile", self.namespace).attrib["full-path"]  # type: ignore

    def get_spine(self):
        with self.zip_ref.open(self.opf) as xml_file:
            tree = ET.parse(xml_file)
            spine = tree.find(".//opf:spine", self.namespace)
            for i in spine:  # type: ignore
                self.spine.append(i.attrib["idref"])

    def get_manifest(self):
        with self.zip_ref.open(self.opf) as xml_file:
            tree = ET.parse(xml_file)
            manifest = tree.find(".//opf:manifest", self.namespace)
            for i in manifest:  # type: ignore
                self.manifest.append({"id": i.attrib["id"], "href": i.attrib["href"]})
    
    def get_image(self):
        index = 1
        for itemref in tqdm.tqdm(self.spine):
            for item in self.manifest:
                if itemref == item["id"]:
                    href = item["href"]
                    html_path = os.path.normpath(os.path.join(os.path.dirname(self.opf), href))
                    html_path = html_path.replace("\\", "/")
                    # 尝试打开html或xhtml文件，如果不存在，则忽略
                    try:
                        with self.zip_ref.open(html_path) as html:
                            html_text = html.read().decode()
                            match = re.search(r'<img\s+src\s*=\s*["\']([^"\']+)["\']', html_text)
                            if match == None:
                                match = re.search(r'\bxlink:href\s*=\s*["\']([^"\']*)["\']', html_text)
                            if match:
                                path = os.path.normpath(os.path.join(os.path.dirname(html_path), match.group(1)))
                                path = path.replace("\\", "/")
                                extension = os.path.splitext(path)[1]
                                # 尝试打开image文件，如果不存在，则忽略
                                try:
                                    with self.zip_ref.open(path) as img:
                                        self.zipf.writestr(f"{index:03}_{item["id"]}{extension}", img.read())
                                    index += 1
                                except:
                                    pass
                            break
                    except:
                        pass
                    
    def get_metadata(self):
        with self.zip_ref.open(self.opf) as xml_file:
            tree = ET.parse(xml_file)
            element = tree.find(".//opf:metadata", self.namespace)
            element = element.findall(".//dc:*", self.namespace) # type: ignore
            epub_metadata: dict[str, list] = {}
            for elem in element:
                local_name = elem.tag.split('}')[1]
                if epub_metadata.get(local_name) == None:
                    epub_metadata[local_name] = []
                epub_metadata[local_name].append(elem.text.strip() if elem.text else '')
            
            if epub_metadata.get('title') != None:
                self.metadata['Title'] = ', '.join(epub_metadata['title'])
            if epub_metadata.get('creator') != None:
                self.metadata['Writer'] = ', '.join(epub_metadata['creator'])
            if epub_metadata.get('description') != None:
                self.metadata['Summary'] = ', '.join(epub_metadata['description'])
            if epub_metadata.get('publisher') != None:
                self.metadata['Publisher'] = ', '.join(epub_metadata['publisher'])
            if epub_metadata.get('series') != None:
                self.metadata['Series'] = ', '.join(epub_metadata['series'])
            if epub_metadata.get('language') != None:
                self.metadata['LanguageISO'] = ', '.join(epub_metadata['language'])
            if epub_metadata.get('identifier') != None:
                self.metadata['GTIN'] = ', '.join(epub_metadata['identifier'])
            
            
    def set_metadata(self):
        root = ET.Element("ComicInfo")
        root.attrib["xmlns:xsi"] = "https://www.w3.org/2001/XMLSchema-instance"
        root.attrib["xmlns:xsd"] = "https://www.w3.org/2001/XMLSchema"
        
        items = self.metadata.items()
        for key, value in items:
            dc_title = ET.SubElement(root, key)
            dc_title.text = value
            
        xml_text = ET.tostring(root, encoding='utf-8').decode('utf-8')
        self.zipf.writestr("ComicInfo.xml", xml_text)


    def main(self, epub_path: str, output: str):
        self.zipf = zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=4)
        self.read_epub(epub_path)
        self.get_metadata()
        self.set_metadata()
        self.get_spine()
        self.get_manifest()
        self.get_image()
        self.zip_ref.close()
        self.zipf.close()
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="epub to cbz")
    parser.add_argument("input", type=str, help="The directory of files that need to be converted")
    parser.add_argument("output", type=str, help="The directory where the converted files are stored")
    
    args = parser.parse_args()
    
    input = args.input
    output = args.output
    for root, dirs, files in os.walk(input):
        for f in files:
            if os.path.splitext(f)[1] == ".epub":  # 处理epub
                input_epub_path = os.path.join(root, f)
                output_epub_path = input_epub_path.replace(input, output)
                output_dir = os.path.dirname(output_epub_path)
                if not os.path.exists(output_dir):
                    os.mkdir(output_dir)
                output_epub_path = output_epub_path.replace(".kepub", "")
                output_epub_path = output_epub_path.replace(".epub", ".cbz")
                if os.path.exists(output_epub_path):
                    continue
                print(input_epub_path)
                epub2cbz().main(input_epub_path, output_epub_path)
