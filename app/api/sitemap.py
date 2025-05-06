from fastapi import APIRouter, Response
from datetime import datetime
from typing import List
import xml.etree.ElementTree as ET
from xml.dom import minidom

router = APIRouter()

def prettify(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

@router.get("/sitemap.xml")
async def generate_sitemap():
    # Create the root element
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    
    # Add static pages
    static_pages = [
        ("/", "1.0", "weekly"),
        ("/about", "0.6", "monthly"),
    ]
    
    for path, priority, changefreq in static_pages:
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = f"https://gpmap.opengwas.io{path}"
        ET.SubElement(url, "lastmod").text = datetime.now().strftime("%Y-%m-%d")
        ET.SubElement(url, "changefreq").text = changefreq
        ET.SubElement(url, "priority").text = priority

    # TODO: Add dynamic pages from your database
    # Example:
    # for gene in get_top_genes():
    #     url = ET.SubElement(urlset, "url")
    #     ET.SubElement(url, "loc").text = f"https://gpmap.opengwas.io/gene?id={gene.id}"
    #     ET.SubElement(url, "lastmod").text = gene.last_modified.strftime("%Y-%m-%d")
    #     ET.SubElement(url, "changefreq").text = "weekly"
    #     ET.SubElement(url, "priority").text = "0.8"

    # Generate the XML
    sitemap_xml = prettify(urlset)
    
    return Response(
        content=sitemap_xml,
        media_type="application/xml"
    ) 