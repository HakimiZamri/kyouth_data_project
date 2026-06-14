from email import message_from_bytes
from email.policy import default
import quopri
import os

def ingest_all_mhtml(input_dir, output_dir):

    if not os.path.exists(input_dir):
        print(f"Warning: {input_dir} does not exists. Creating directory...")
    
    os.makedirs(output_dir, exist_ok=True)

    print("Bronze:...")

    count = 0
    extcount = 0
    failedcount = 0

    for raw in input_dir.glob("*.mhtml"):
        count += 1
        has_html = False
        filename = raw.stem

        with open(raw, 'rb') as file:
            msg = message_from_bytes(file.read(), policy=default)

        html_parts = []

        for part in msg.walk():
            if part.get_content_type() == "text/html":
                # html = part.get_payload(decode=True).decode("utf-8")
                html = part.get_payload()
                html_decode = quopri.decodestring(html).decode("utf-8")
                html_parts.append(html_decode)
                has_html = True

        file_output = output_dir / f"{filename}.html"

        with open(file_output, 'w', encoding="utf-8") as fw:
            fw.write("\n".join(html_parts))

        if has_html:
            print(f"Extracted: {filename}.mhtml")
            extcount += 1

        else:
            print(f"No HTML content found in: {filename}.mhtml")
            failedcount += 1

    print("Bronze Summary:")
    print(f"Total: {count} | Extracted: {extcount} | Failed: {failedcount}")
        
