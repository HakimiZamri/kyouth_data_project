from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError
import json
import os


class JobListing(BaseModel):
    source_id: str
    job_title: str
    company: str
    description: str


def process_all_html(input_dir, output_dir):

    if not os.path.exists(input_dir):
        print(f"Warning: Please run ingest first or create {input_dir}")

    os.makedirs(output_dir, exist_ok=True)

    print("Silver:...")

    count = 0
    processed = 0
    skipped = 0

    for bronze in input_dir.glob("*.html"):
        filename = bronze.stem
        count += 1

        with open(bronze, "rb") as file:
            soup = BeautifulSoup(file, "html.parser")

        # clean_txt = soup.get_text(separator=" ", strip=True)

        source = soup.find("meta", property="og:url")
        source_id = source.get("content").split("/")[-1] if source else None

        if source_id is None or source_id == "":
            print(f"Missing source_id in: {filename}.html")
            skipped += 1
            continue

        else:
            source_id = source_id

        title = soup.find("h1", attrs={"data-automation": "job-detail-title"})
        job_title = title.get_text(separator=" ", strip=True) if title else None

        if job_title is None or job_title == "":
            print(f"Missing job_title in: {filename}.html")
            skipped += 1
            continue

        else:
            job_title = job_title

        company = soup.find("span", attrs={"data-automation": "advertiser-name"})
        company_name = company.get_text(separator=" ", strip=True) if company else None

        if company_name is None or company_name == "":
            print(f"Missing company in: {filename}.html")
            skipped += 1
            continue

        else:
            company_name = company_name

        desc = soup.find("div", attrs={"data-automation": "jobAdDetails"})
        job_desc = desc.get_text(separator=" ", strip=True) if desc else None

        if job_desc is None or job_desc == "":
            print(f"Missing description in: {filename}.html")
            skipped += 1
            continue

        else:
            job_desc = job_desc

        try:
            detail = JobListing(
                source_id=source_id,
                job_title=job_title,
                company=company_name,
                description=job_desc,
            )
        
        except ValidationError as e:
            print(f"Validation failed: {e}")
            continue

        file_output = output_dir / f"{filename}.json"
        with open(file_output, "w", encoding="utf-8") as fw:
            json.dump(detail.model_dump(), fw, indent=4, ensure_ascii=False)

        print(f"Processed: {filename}.html")
        processed += 1

    print("Silver Summary:")
    print(f"Total: {count} | Processed: {processed} | Skipped: {skipped}")
