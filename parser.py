import csv
from models import Person

def parse_csv(filepath: str) -> tuple[list[Person], list[str]]:
    people = []
    warnings = []

    with open(filepath, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            try:
                rank = row['Rank'].strip()
                name = row['Name'].strip()
                platoon = row['Platoon'].strip()
                appt = row['Appt'].strip()
                avail_raw = row['Availability'].strip()
                available = avail_raw == '1'

                if not name:
                    warnings.append(f"Row {i}: empty name, skipping.")
                    continue

                people.append(Person(rank=rank, name=name, platoon=platoon,
                                     appt=appt, available=available))
            except KeyError as e:
                warnings.append(f"Row {i}: missing column {e}, skipping.")

    initiators = [p for p in people if p.is_initiator and p.available]
    if not initiators:
        warnings.append("WARNING: No available initiators (OC/CSM/2IC) found. Recall cannot start.")

    unavail = [p for p in people if not p.available]
    if unavail:
        warnings.append(f"Note: {len(unavail)} personnel unavailable and excluded from call chain.")

    return people, warnings
