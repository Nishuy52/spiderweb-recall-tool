import csv, random
random.seed(42)

rows = []

rows += [
    ("LTA", "James Tan",    "HQ", "OC",  1),
    ("LTA", "Wei Ming",     "HQ", "2IC", 1),
    ("1SG", "Kumar Raj",    "HQ", "CSM", 1),
    ("2SG", "Hafiz Ismail", "HQ", "",    1),
    ("2SG", "Lim Ah Kow",  "HQ", "",    1),
    ("3SG", "Derek Chan",   "HQ", "",    1),
    ("3SG", "Alvin Goh",    "HQ", "",    1),
    ("3SG", "Ben Tan",      "HQ", "",    0),
    ("CPL", "Chris Wong",   "HQ", "",    1),
    ("CPL", "Dave Seah",    "HQ", "",    1),
    ("CPL", "Eric Low",     "HQ", "",    0),
    ("PTE", "Frank Yeo",    "HQ", "",    1),
    ("PTE", "Gary Sim",     "HQ", "",    1),
    ("PTE", "Henry Poh",    "HQ", "",    1),
    ("PTE", "Ivan Chua",    "HQ", "",    0),
]

platoons = [
    ("1", "Farid Hassan",  "Rajan Singh"),
    ("2", "Chen Wei Jie",  "David Lim"),
    ("3", "Zach Lim",      "Ken Ho"),
    ("4", "Ryan Teo",      "Marcus Lee"),
]

def namelist(prefix, names):
    return [f"{prefix} {n}" for n in names]

sgts_2sg = namelist("2SG", [
    "Ahmad","Benny","Calvin","Danny","Eugene","Felix",
    "Gordon","Henry","Ivan","Jason","Kevin","Leon",
    "Martin","Nathan","Oscar","Peter"
])
sgts_3sg = namelist("3SG", [
    "Quentin","Roger","Samuel","Thomas","Andy","Bobby",
    "Casey","Dean","Eddie","Faris","Glenn","Hugo",
    "Ian","Jarvis","Kent","Larry","Manny","Neil","Owen","Percy"
])
cpls = namelist("CPL", [
    "Ricky","Sean","Terry","Ulric","Victor","Wayne","Xavier","Yusuf",
    "Zane","Aaron","Blake","Clyde","Dylan","Evan","Fred","Gus",
    "Hank","Ike","Joel","Karl","Liam","Mark","Ned","Otto",
    "Paul","Raj","Sam","Ted","Umar","Van","Will","Xav"
])
ptes = namelist("PTE", [
    "Adam","Brad","Carl","Dale","Elmo","Yew","Zen","Ali",
    "Cai","Dan","Ed","Fai","Goh","Hai","Iqbal","Jun",
    "Kai","Lee","Naz","Ong","Poh","Qin","Rox","Suresh",
    "Tan","Uma","Vince","Wee","Yap","Zul","Ben","Joe",
    "Tim","Ray","Jay","Kay","Rex","Dex","Lex","Hex",
    "Max","Pax","Jax","Fox","Cox","Knox","Rox2","Nox"
])

r2 = iter(sgts_2sg)
r3 = iter(sgts_3sg)
rc = iter(cpls)
rp = iter(ptes)

def av(miss=0.1):
    return 0 if random.random() < miss else 1

for plt, plc, pls in platoons:
    rows.append(("2LT", plc, plt, "PL COMD", 1))
    rows.append(("1SG", pls, plt, "PL SGT",  1))
    for _ in range(3):  rows.append(("2SG", next(r2), plt, "", av(0.08)))
    for _ in range(4):  rows.append(("3SG", next(r3), plt, "", av(0.10)))
    for _ in range(7):  rows.append(("CPL", next(rc), plt, "", av(0.10)))
    for _ in range(10): rows.append(("PTE", next(rp), plt, "", av(0.12)))

with open("/home/claude/recall_tool/company.csv","w",newline="") as f:
    w = csv.writer(f)
    w.writerow(["Rank","Name","Platoon","Appt","Availability"])
    w.writerows(rows)

total = len(rows)
avail = sum(1 for r in rows if r[4]==1)
print(f"Generated {total} personnel, {avail} available")
for plt in ["HQ","1","2","3","4"]:
    n = sum(1 for r in rows if r[2]==plt)
    a = sum(1 for r in rows if r[2]==plt and r[4]==1)
    print(f"  Platoon {plt}: {n} total, {a} available")
