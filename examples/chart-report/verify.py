"""Check the supplied synthetic A/B chart reports, including embedded pixels."""
import hashlib, json, pathlib, sys, xml.etree.ElementTree as ET
from PIL import Image, ImageChops, ImageStat
from pypdf import PdfReader

EXPECTED = {
    'A': {'column': [18, 32, 24, 41], 'line': [12, 21, 17, 29]},
    'B': {'column': [38, 14, 43, 22], 'line': [31, 13, 35, 19]},
}
TITLES = {'column': 'Completed tasks', 'line': 'Support requests'}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate(folder, dataset):
    folder = pathlib.Path(folder)
    assert dataset in EXPECTED
    png_images, findings = [], {}
    for kind, values in EXPECTED[dataset].items():
        svg_path, png_path = folder/f'{kind}.svg', folder/f'{kind}.png'
        svg = ET.parse(svg_path).getroot()
        assert svg.attrib['width'] == '800' and svg.attrib['height'] == '450', svg.attrib
        elements = list(svg.iter())
        tags = [e.tag.rsplit('}', 1)[-1].lower() for e in elements]
        assert not {'script', 'animate', 'animatetransform', 'foreignobject'}.intersection(tags)
        assert len([t for t in tags if t in {'rect', 'path', 'polyline', 'line', 'circle'}]) > 8
        text_nodes = [''.join(e.itertext()).strip() for e in elements if e.tag.rsplit('}',1)[-1] == 'text']
        for expected in [TITLES[kind], 'Week 1', 'Week 2', 'Week 3', 'Week 4', *map(str, values)]:
            assert expected in text_nodes, (kind, expected, text_nodes)
        legend = [''.join(e.itertext()).strip() for e in elements if 'legend-label' in e.attrib.get('class', '').split()]
        assert ('Completed' if kind == 'column' else 'Requests') in legend, legend
        assert ':hover' not in svg_path.read_text()
        with Image.open(png_path) as image:
            assert image.format == 'PNG' and image.size == (1600, 900), (image.format,image.size)
            rgb = image.convert('RGB')
            assert min(ImageStat.Stat(rgb).stddev) > 12, ImageStat.Stat(rgb).stddev
            # Preserve decoded pixels independently of the program's success message.
            png_images.append(rgb.copy())
        findings[kind] = {'svg_sha256':digest(svg_path), 'png_sha256':digest(png_path), 'size':[1600,900]}
    pdf_path = folder/'report.pdf'
    assert pdf_path.read_bytes().startswith(b'%PDF-')
    reader = PdfReader(pdf_path)
    assert len(reader.pages) == 1, len(reader.pages)
    text = '\n'.join(page.extract_text() for page in reader.pages)
    for expected in [f'Weekly team report - sample {dataset}', 'Column chart', 'Line chart', 'Synthetic sample data', *[', '.join(map(str,v)) for v in EXPECTED[dataset].values()]]:
        assert expected in text, (expected, text)
    embedded = []
    for page in reader.pages:
        for ref in page['/Resources'].get('/XObject',{}).values():
            obj = ref.get_object()
            if obj.get('/Subtype') == '/Image':
                assert (obj['/Width'],obj['/Height']) == (1600,900)
        embedded.extend(image.image.convert('RGB') for image in page.images)
    assert len(embedded) == 2, len(embedded)
    # Exact decoded-pixel equality proves the generated PNGs reached the PDF.
    for png in png_images:
        assert any(png.size == im.size and ImageChops.difference(png,im).getbbox() is None for im in embedded), 'PNG pixels absent from PDF'
    findings['pdf'] = {'sha256':digest(pdf_path),'pages':len(reader.pages),'images':len(embedded),'text':text}
    return findings

if __name__ == '__main__':
    if len(sys.argv) not in (3, 4):
        raise SystemExit('Usage: python verify.py OUTPUT_DIRECTORY A|B [OTHER_SAMPLE_DIRECTORY]')
    result=validate(sys.argv[1],sys.argv[2])
    if len(sys.argv)>3:
        other=validate(sys.argv[3], 'B' if sys.argv[2]=='A' else 'A')
        for kind in ('column','line'):
            assert result[kind]['svg_sha256'] != other[kind]['svg_sha256']
            assert result[kind]['png_sha256'] != other[kind]['png_sha256']
            with Image.open(pathlib.Path(sys.argv[1])/f'{kind}.png') as a, Image.open(pathlib.Path(sys.argv[3])/f'{kind}.png') as b:
                # Inner plot only excludes differences limited to titles/captions.
                diff=ImageChops.difference(a.convert('RGB').crop((180,200,1480,670)), b.convert('RGB').crop((180,200,1480,670)))
                assert sum(ImageStat.Stat(diff).mean)>5, ImageStat.Stat(diff).mean
        assert result['pdf']['sha256'] != other['pdf']['sha256']
        result['comparison']='A/B SVG, PNG, PDF and plot pixels differ'
    print(json.dumps(result,indent=2))
