# Section 03 — Jeepney Routes EDA

Content and script for slides **12–21** of the THS-2 demo deck, filling the group's existing
placeholders on pages 12–20. Agreement-form item 3: *"Analyze the current jeepney route
network and report the detailed results."*

**Built deck:** <https://claude.ai/artifact/Kefzp5rAuq2rnGRhfguqaH> — ten slides in the THS-2
house style. The speaker notes on each slide are the scripts below.

## How this is built

The adviser's pointers, applied:

| Pointer | How it shows up here |
|---|---|
| Be as specific as possible about what you did | Every bullet names the number, the parameter or the file |
| Same level of detail as the methodology | Method on the slide, detail in the script |
| Talk about deviations from the methodology and why | **No longer a callout.** Each one is now a plain bullet or a line in the script — see *Where the deviations went* |
| Add flowcharts to show the pipeline | Slide 12 is the EDA pipeline, as four input boxes feeding one build step |
| Show the data, then how you interpret it | Left column reads the data, right column shows it |
| Don't just show data, explain the decisions | The coral takeaway line under the bullets is the decision, not the number |
| Show what's next for unfinished work | Slide 21 closes with the four open items |
| No code screenshots | None |

**Pattern per slide:** `03 Jeepney Routes EDA` header → sub-heading → three bullets →
takeaway line → picture or table on the right.

**Pattern per script:** *what we did* → *what came out* → *what it means, and where the
decision came from*. The section opens mid-stream, continuing from 01 and 02 — it does not
re-introduce the inputs or their provenance, which those sections already covered.

**Timing:** 10 slides, about 12–14 minutes with questions. This is one of six agreement items
in a 30–45 minute presentation, so it can run longer than a defense slot would allow.

**Cities:** Makati, Manila, Taguig. Mandaluyong is built and loadable but not presented.

> **All numbers below were recomputed on 2026-11-23 after pulling 33 commits.** Several moved.
> See *What changed since the last version* at the end before reusing any older figure.

## Design system

Measured from `THS-2 Slides-1.pdf` and the page-7 render, not guessed. Canvas 1920 × 1080,
white field. Every page of the group's deck embeds **League Spartan Bold**; body copy is
**Lato**, and tables are **Roboto**.

**Two different units, and they get confused.** Canva's size field is **points**. This
document and `deck.css` are in **pixels** on the 1920-wide canvas. The design is 20 inches
wide at 96 dpi, so:

> **px = pt × 1.333**  ·  Canva 16 → 21 px · Canva 40 → 54 px · Canva 73 → 98 px

| | font | Canva (pt) | at 1920 (px) | colour |
|---|---|---|---|---|
| Section number (`03`) | League Spartan Bold | 105 | 140 px | `#DD6B6C` |
| Section name (`Jeepney Routes EDA`) | League Spartan Bold | 73 | 98 px | `#000000` |
| Slide sub-heading | League Spartan Bold | 44 | 58 px | `#000000` |
| Body / bullets | Lato Regular, Bold for emphasis | 40 | 54 px, 79 px line pitch | `#1A1A1A` |
| **Tables** | **Roboto** — headers and row labels bold, values regular | **16** | **21 px** | `#000000` / `#1A1A1A` |
| Captions | Lato Regular | 14 | 19 px | `#6B6B6B` |

Tables at 16 pt are **two and a half times smaller than the body text**, and are the
smallest thing in the deck. That is the group's own choice and it matches the caption sizes
in the THS-1 deck, but it is at the bottom of what reads from the back of a room — worth a
look on the projector before the demo rather than after.

Grid, from the measured render: section number at x 11, section name at x 207, both on one
baseline at the top · left text column starts at **x 82**, sub-heading at y 205, first bullet
line at y 294 · bullet marker at x 130, text at x 177 · **picture column x 1125–1825**,
y 160–1030.

**The text is big, and that is the constraint.** The body column wraps at **33–36 characters**
a line. Measured on the reference slide, the whole left column is a sub-heading plus about
**eight lines** — so each slide gets three bullets of two to three lines and nothing more.
Everything else belongs in the script. `scratchpad/fitcheck.py` checks each slide against the
848 px box.

**Spelling:** the group's slides use Commonwealth forms (`modelled`, `categorises`), so this
document and the deck both use `optimiser` / `analyse`.

## The overlap map's colours

Changed after the first review. The ramp ran **cyan to magenta**, chosen to avoid the
yellows and oranges OpenStreetMap paints its own roads in. That avoided the clash and
created a worse problem: single-route arcs are most of the network, so the brightest colour
on the map sat on the least important value, and the corridors the figure exists to show had
to compete with it.

What it is now, in `src/analysis/figures.py`:

| | |
|---|---|
| Ramp | `OVERLAY_STOPS` = `#8295A6` slate &#8594; `#DD6B6C` coral &#8594; `#5C0A14` crimson |
| Ordered by | **lightness, not hue** &#8212; "more routes" reads as "darker" without the key, and survives colour-blind viewing |
| Line width | `1.3 + 4.2 x normalised count`, so width carries the same number as colour |
| Basemap | `fade=True` is now the default; tiles keep streets, labels and coastline but lose their colour |

The ramp and the fade depend on each other: a reddish ramp is only safe once the tiles are
desaturated, because OSM draws motorways and trunk roads in pinks and reds. Passing
`fade=False` means also passing a `cmap` that avoids yellow, orange and red.

Regenerated 2026-11-23: `overlap_map_manila.png`, `overlap_map_taguig.png`,
`overlap_map_makati.png`.

## Where the deviations went

The four deviation callouts were removed. The findings behind them stayed; the two that are
genuinely corrections to the proposal are now spoken rather than boxed. Nothing is hidden.

| Was a callout on | Now |
|---|---|
| 13 — Taft Avenue is not the worst corridor | Last paragraph of slide 13's script |
| 14 — the catchment radius was left open | Slide 14's takeaway line, *500 m is now fixed as CATCHMENT_RADIUS_M* |
| 16 — the proposal never said how a stop gets its ω | Slide 16's script; the slide shows the three rules instead |
| 19 — one parameter doing two jobs | Slide 19, third bullet and the takeaway line |

---

## Slide 12 — What this section does

**Header:** `03` *Jeepney Routes EDA* — constant across the section.

**Bullets (left column):**

- Sections 01 and 02 built the data. This one **measures the network**.
- One graph per city: every stop a point, **every route leg its own link**.
- Five routes down one street stay **five links** — that is what makes overlap countable.

**Right column:** 5 accent-rule boxes

- **01 · Route overlaps** — how much road carries more than one route
- **02 · Commuter flows** — who can walk to a stop, and at what radius
- **03 · Network connectivity** — whether each city is one network at all
- **04 · Capacity and cost** — what the stops that exist would cost to build
- **05 · 06 · Sizing, spacing, pool** — three assumptions in the algorithm, tested

*Caption:* Six measurements. Four of them changed something in the algorithm we proposed.

**Script:**

Sections one and two built the data. This section measures the network that data describes: the jeepney network as it runs today, before we change anything.

What we did. For each city we built one graph. Every stop is a point, and every time a route travels one stretch of road we add a separate link. Five routes down the same street means five links, not one.

Why we built it that way. The usual shortcut is one link per road. We needed to count how many routes share a road, and that shortcut throws the count away before you can count it. Keeping the routes apart is what makes the next slide possible at all.

Each link also stores the road path the route actually follows, not a straight line between stops. Without that, route length is wrong everywhere a road bends, and every distance measure built on it is wrong too.

Six measurements come off that graph. Four of them changed something in the algorithm we proposed, and one is a problem we have to fix before we can run it.

---

## Slide 13 — Route Overlaps

**Header:** `03` *Jeepney Routes EDA* — constant across the section.

**Bullets (left column):**

- **62%** of the road Manila’s jeepneys serve carries three or more routes.
- The worst arc is **Carlos Palanca, 107 routes**. The top five all sit in the Quiapo–Santa Cruz grid.
- Makati and Taguig stack far less — about **2.5** routes per served arc.

**Right column:** `plots/eda/overlap_map_manila.png`

*Caption:* Manila · routes per road arc. Slate 1 route, crimson 107; thickness carries the same number. The basemap is drained of colour so the routes are the only coloured thing on it.

**Script:**

What we did. For every stretch of road in each city, we counted how many separate jeepney routes use it.

What came out. In Manila, sixty-two percent of the road that carries jeepneys carries three or more routes. The average stretch carries about ten. The worst single stretch, Carlos Palanca in Quiapo, carries a hundred and seven.

The top five are all within about six hundred metres of each other in the old downtown grid: Carlos Palanca, Ronquillo, Villalobos, Recto and Rizal Avenue. The duplication is concentrated in one place rather than spread across the city, which means the redundancy objective has a specific area to work on.

Makati and Taguig are different. Both average about two and a half routes per stretch, so we should expect much smaller gains there.

On the map, two things are deliberate. Colour and thickness both carry the same number, so the heavy corridors are findable from the back of the room. And the basemap is drained of colour, so the routes are the only coloured thing on it. Our first version had the routes running cyan to magenta: single-route roads are most of the network, so that put the brightest colour on the least important value.

If you ask about Taft Avenue, which our proposal used as the example: we picked it from a photograph before anyone counted. It is not in the top eight. The pattern is real, the example was wrong.

---

## Slide 14 — Commuter Flows

**Header:** `03` *Jeepney Routes EDA* — constant across the section.

**Bullets (left column):**

- No ridership data. Demand comes from **30 m population cells**.
- A cell served by *n* stops gives **1/*n* to each**, so nobody is counted twice.
- Reach at 500 m: **54% / 90% / 54%**. At 1000 m the sum is **39×** that.

**Takeaway line:** 500 m is now fixed as CATCHMENT_RADIUS_M

**Right column:** `plots/eda/catchment_radius.png`, a compact table

| Radius | Mak | Man | Tag | Counted |
|---|---|---|---|---|
| 500 m | 54% | 90% | 54% | 3.1–11.0× |
| 750 m | 61% | 95% | 70% | 4.9–22.9× |
| 1000 m | 65% | 97% | 85% | 6.7–39.4× |

*Caption:* Left: population reached. Right: how many times the average resident is counted.

**Script:**

What we did. There is no ridership data for jeepneys, so we estimate demand from where people live. We take a population grid at thirty-metre squares, and for each stop we collect every square within five hundred metres of it.

One step matters more than the rest. If a square is within walking distance of three stops, we give each stop a third of those people rather than all of them. Without that, the same resident is counted at every nearby stop and every per-stop number comes out inflated.

What came out. Manila reaches ninety percent of its residents. Makati and Taguig both reach fifty-four. Close to half of each of those cities cannot walk to a jeepney stop.

Where the five hundred metres came from. Our proposal left this open across three values, so we measured all three. Look at the last column of the table. At one kilometre the stop catchments in Manila add up to thirty-nine times the number of people actually reached, because everybody falls inside dozens of stops at once. That is not more reach, it is more double counting. A kilometre is also further than the literature says people will walk, which is around eight hundred metres.

So five hundred is a fixed value in the config now, and the user cost objective reads the same one. Reach and cost cannot drift apart that way.

Manila being so much higher is density, not better planning.

---

## Slide 15 — Network Connectivity

**Header:** `03` *Jeepney Routes EDA* — constant across the section.

**Bullets (left column):**

- Taguig breaks into **five pieces** — three near-even: **31%**, 29%, 25%.
- Only **24%** of its stop pairs can reach each other.
- Makati is one network. Manila is five, but **96%** is one piece.

**Takeaway line:** If the optimiser cannot improve Taguig, it is not working

**Right column:** `plots/eda/overlap_map_taguig.png`

*Caption:* Taguig · routes per road arc. The roads touch in places, but the routes do not share a stop there, so a passenger cannot change between them.

**Script:**

What we did. We asked one question of each network: starting from any stop, which other stops can you actually reach by jeepney, changing routes as often as you like?

What came out. Makati is one network, every stop reaches every other. Manila breaks into five pieces, but ninety-six percent of its stops are in the main one, so it behaves as one. Taguig breaks into five pieces that are nearly even: thirty-one percent, twenty-nine, twenty-five, and two small ones. Only twenty-four percent of Taguig stop pairs can reach each other.

One thing to be careful about on the map. The lines look joined, and in places the roads genuinely are. Two routes can run through the same junction without either one stopping there, and if neither stops you cannot change between them. The Bonifacio cluster and the corridor running south along the lake are the clearest case: next to each other on the ground, separate on the network.

Twenty-four percent is also the generous reading. That figure lets you transfer as many times as you like, free. A real passenger pays again each time.

What we take from it. Taguig is where the optimiser has the most room. If the results come back and Taguig has not improved, the problem is our algorithm rather than the city.

---

## Slide 16 — Capacity Constraints — three ways to size a stop

**Header:** `03` *Jeepney Routes EDA* — constant across the section.

**Layout:** no picture column. The text column runs the full width
(`style="width:1756px"`), which is the only slide in the section that does.
With four bullets at two lines each it comes to 833 px of the 848 px box.

**Bullets (full width):**

- No Philippine standard exists, so we based this on **Singapore's Land Transport Authority** table, at **₱28,000 per m²**.
- **By routes at the stop.** How many meet there, cut at thresholds already in our config. This is what the algorithm does now.
- **By routes, tuned per city.** The same count, but cut-offs from each city's own spread rather than one global set.
- **By people nearby.** Residents within walking distance, and how many board in the peak hour. This is what the table measures.

**Takeaway line:** none — "three ways" moved into the sub-heading, which saved
the line the fourth bullet needed.

**Script:**

What we did. To price a network we need a price per stop, and that depends on how big each stop is.

There is no Philippine standard for sizing a jeepney stop. The closest published one we found is Singapore's Land Transport Authority design criteria, section four point two. It sets how much shelter floor area a stop needs for a given number of passengers boarding per hour: eleven sizes, from eighteen square metres up to a hundred and eight, all three metres wide.

I want to be clear that this is a basis, not a local standard. Singapore's buses and our jeepneys are different vehicles in a different city, so what we take from it is the relationship — more passengers, more shelter — rather than the absolute figures. The money is local: twenty-eight thousand pesos per square metre comes from Philippine PUV shelter estimates already in our config.

The hard part is not the size table. It is deciding which size a given stop should be, and our proposal never said. So we costed three different ways of deciding it, which are the last three lines.

The first goes by how many jeepney routes meet at the stop, using cut-offs already written into our config. That is what the algorithm does today, so it is the one we have to beat.

The second counts the same thing but sets the cut-offs separately for each city, so a busy stop in Taguig is judged against Taguig rather than against Manila.

The third ignores routes and looks at people instead: how many residents live within walking distance, then an estimate of how many of them board in the peak hour. That is the quantity the Singapore table was actually built around, so it is the one that uses the source as intended.

The next two slides are the evidence for which of the three holds up.

If you ask about that boarding estimate, we use five percent. The sensitivity is in backup and it moves Manila by about two and a half times, so it is the weakest number in the cost model.

---

## Slide 17 — Capacity Constraints — the budget

**Header:** `03` *Jeepney Routes EDA* — constant across the section.

**Bullets (left column):**

- Manila’s existing stops cost **₱697 M**. MAX_BUDGET is **₱200 M**, one value for all three cities.
- Manila is **1.9–3.5× over** under every rule, so a constrained run must return something worse.
- Makati fits, at **87% of the cap**.

**Takeaway line:** Set the budget per city, from these numbers

**Right column:** `plots/eda/capex_options.png`, a compact table

| Sizing rule | Makati | Manila | Taguig |
|---|---|---|---|
| 01 Degree, config | 173 | 697 | 141 |
| 02 Degree, terciles | 135 | 560 | 116 |
| 03 Catchment, 5% | 74 | 387 | 100 |
| MAX_BUDGET | 200 | 200 | 200 |

*Caption:* PHP million. Cost of the stops that already exist, against the configured cap.

**Script:**

What we did. We took the stops that already exist and priced them under each of the three rules.

What came out. Under the rule the algorithm uses today, Manila's existing stops come to six hundred ninety-seven million pesos. Our budget cap is two hundred million, and it is one figure applied to all three cities.

So the cap rules out the network that is already on the ground. Anything the optimiser returns for Manila under that cap has to be smaller than what exists now, and objective three compares exactly those two things. Even under the cheapest of the three rules Manila is nearly twice over.

Makati fits, but only just: a hundred seventy-three million against a two hundred million cap. That leaves thirteen percent of a budget to build anything new with.

What follows from it. The cap was a number we chose, not a constraint anyone handed us. These measurements are the first basis we have had for setting it, so it should be set per city from them, and before we run rather than after.

If you ask what the optimiser is for when the current network is already over budget: the unconstrained run is already part of objective three, as its second comparison point.

One note on the numbers. The CSV reads seven hundred ninety-seven million for Manila. The difference is a hundred-million penalty the fitness function folds into the figure it returns. The slide shows the build cost.

---

## Slide 18 — Stop Sizing

**Header:** `03` *Jeepney Routes EDA* — constant across the section.

**Bullets (left column):**

- Rules 01 and 02 assume **degree stands in for demand**. We tested it.
- The correlation is **+0.11** in Makati, **−0.12** in Manila, **+0.03** in Taguig.
- The signs do not agree across three cities in one metro area.

**Takeaway line:** Degree is not a demand proxy

**Right column:** a compact table

| Degree vs residents | Makati | Manila | Taguig |
|---|---|---|---|
| Apportioned catchment | +0.11 | −0.12 | +0.03 |
| Raw catchment | +0.19 | −0.14 | −0.05 |

*Caption:* Pearson correlation over all stops per city. The apportioned row is the one that matters — raw catchment counts the same resident at every nearby stop. Scatter plots per city are in backup.

**Script:**

What we did. Two of the three rules size a stop by how many routes meet there, on the assumption that a busier junction serves more people. We had not checked that assumption, so we checked it.

For every stop in every city we compared the number of routes meeting there against the number of residents that stop serves.

What came out. The relationship is weakly positive in Makati, almost nothing in Taguig, and negative in Manila. The signs do not agree across three cities in the same metro area.

What it means. How many routes meet at a stop does not tell you how many people it serves, so we cannot describe it as a stand-in for demand.

It may still be the right thing to size by. A stop where five routes meet needs physical room for five vehicles whether or not anyone is waiting. That is a real argument. It is just an argument about vehicles rather than passengers, and we should be clear which one we are making.

The rule that goes by catchment is the one with evidence behind it.

The scatter plots are in backup if you want them: three panels, routes across, residents up, no trend in any of them.

This is the sort of thing the EDA was for. We would have shipped the assumption otherwise.

---

## Slide 19 — Stop Spacing

**Header:** `03` *Jeepney Routes EDA* — constant across the section.

**Bullets (left column):**

- The generator spaces stops by one walking distance — a **750 m floor**.
- Real median gaps: Makati **281 m**, Taguig **300 m**. **94%** sit below the floor.
- One parameter sets both walking distance and stop spacing.

**Takeaway line:** Only the walking distance is defensible at 750 m

**Right column:** `plots/eda/stop_spacing.png`, a compact table

|   | Median gap | Below the floor |
|---|---|---|
| Makati | 281 m | 94.0% |
| Taguig | 300 m | 94.9% |
| Manila | 518 m | 65.1% |

*Caption:* Real consecutive-stop gaps against the three configured walking distances.

**Script:**

What we did. We measured how far apart consecutive stops sit on real jeepney routes, and compared that against the closest our generator can place two stops.

Where the generator's floor comes from. When it builds a route it places each stop at least one walking distance from the last. The config points at the middle of three walking distances, so the closest it can ever place two stops is seven hundred fifty metres.

What came out. Real consecutive stops in Makati sit two hundred eighty-one metres apart at the median, Taguig three hundred. Ninety-four percent of real gaps are shorter than the closest our generator can produce.

Manila's median is higher at five hundred eighteen, but a quarter of its gaps are over a kilometre. That is the source data being drawn coarsely, not jeepneys behaving differently.

Why it happens. One parameter is being asked to do two jobs. How far a passenger will walk to reach a stop is one question; how far apart stops should sit along a route is a different one. Seven hundred fifty metres is defensible as a walking distance and not as a spacing floor.

Splitting them into two values is on our list. It widens what the optimiser can build without changing any objective, so it is low risk.

On distance: these are measured with the same haversine formula the GA uses. Against the geodesic one the analysis code used before, the difference is about a third of a percent, so nothing here turns on the choice.

---

## Slide 20 — Candidate Stop Pool

**Header:** `03` *Jeepney Routes EDA* — constant across the section.

**Bullets (left column):**

- Pool = **every CZC-tagged road node**: 4,129 in Manila.
- Makati, Manila: a **hybrid** nearly matches it with 1/6 the stops.
- Taguig: the dense pool gains **45 points of reach**.
- Only **33–50%** of real stops sit within 20 m of a candidate.

**Takeaway line:** The search space excludes our baseline

**Layout:** `.wrap narrow` with `.pic wide`. Four two-line bullets and a one-line
takeaway measure 823 px of the 848 px box.

**Right column:** a compact table

| Basis | Stops | Reach | Cost floor |
|---|---|---|---|
| Makati — Sakay stops only | 138 | 54.1% | ₱104 M |
| Makati — derived pool, current | 1,779 | 61.4% | ₱1,345 M |
| **Makati — hybrid, ≥500 m apart** | 221 | 59.7% | ₱167 M |
| Manila — Sakay stops only | 556 | 90.3% | ₱420 M |
| Manila — derived pool, current | 4,129 | 98.3% | ₱3,122 M |
| **Manila — hybrid, ≥500 m apart** | 705 | 98.3% | ₱533 M |
| Taguig — Sakay stops only | 108 | 53.8% | ₱82 M |
| Taguig — derived pool, current | 2,028 | 99.0% | ₱1,533 M |
| **Taguig — hybrid, ≥500 m apart** | 849 | 97.8% | ₱642 M |

*Caption:* Reach at 500 m. Cost floor = every stop built at the smallest LTA size, so the cheapest that basis can possibly be. Hybrid = the real stops plus every candidate at least 500 m from one of them.

**Script:**

What we did. Before the optimiser can place stops, something has to decide which locations it may choose from. Right now that list is every road node the zone classifier tagged. In Manila that is four thousand one hundred and twenty-nine candidate locations, against five hundred fifty-six stops that actually exist.

We priced three options per city: use only the real stops, use the full generated list, or use the real stops plus every generated one that sits at least five hundred metres from a real stop.

What came out differs by city, so there is no single answer here.

Makati and Manila behave the same way. The full generated list buys seven points of reach in Makati and eight in Manila, and the hybrid gets almost all of that with a fraction of the locations: an eighth in Makati, a sixth in Manila, with the cost floor falling in step. Most of the generated list is not earning anything in either city.

Taguig is the opposite. Its real stops reach fifty-four percent of residents and the generated list reaches ninety-nine. That is forty-five points, and no rearrangement of existing stops recovers it, because Taguig does not have stops where its people live. Its hybrid needs eight hundred locations rather than two hundred, because the gaps it is filling are real.

One thing to notice about Makati: even the full generated list only reaches sixty-one percent. The ceiling is not the stop list, it is which roads the zone classifier tagged, so a Makati run cannot cover the city no matter which basis we choose.

The problem underneath all of it is the last bullet. Between a third and a half of real stops have no candidate location within twenty metres, Manila worst at thirty-three percent. The optimiser cannot build the existing network even if that were the best answer, and the existing network is what objective three compares against.

So the recommendation is the hybrid, with the threshold set per city, and the real stops always in the pool. That is the decision I would most like your view on.

If you ask whether the rerun changes this: the list came out within two tenths of a percent across three separate builds. Makati is in the table now; the saved file that held the wrong object was re-saved upstream.

---

## Slide 21 — Baseline Fitness

**Header:** `03` *Jeepney Routes EDA* — constant across the section.

**Bullets (left column):**

- **Z_efficiency**: six structural measures blended into one.
- **Z_CapEx**: build cost. Manila sits 3.5x over budget.
- **Z_user**: travel time, weighted by who lives near a stop.
- Taguig: **half its trips are impossible**, not just slow.

**Takeaway line:** No city wins on all three

**Layout:** `.wrap narrow` (820 px) with `.pic wide tall`. Four bullets at two
lines each plus a one-line takeaway measures 823 px of the 848 px box, so
nothing here can grow by a line without something else coming out.

**Right column:** a compact table. Rows carrying `.sub` are indented and set in
the muted grey, so a reader can see which rows are components and which are the
three objectives.

|   | Makati | Manila | Taguig |
|---|---|---|---|
| **Z_efficiency** | 0.526 | 0.636 | 0.406 |
| Coverage | 0.218 | 0.398 | 0.136 |
| Internal connectivity | 0.760 | 0.750 | 0.745 |
| External connectivity | 0.380 | 0.450 | 0.438 |
| Vulnerability | 0.689 | 0.619 | 0.287 |
| Robustness | 0.720 | 0.856 | 0.243 |
| Redundancy | 0.598 | 0.786 | 0.714 |
| **Z_CapEx** | ₱173 M | ₱697 M | ₱141 M |
| **Z_user (B person-min)** | 4.6 | 233.7 | 9.8 |
| Mean trip, generalised | 19.1 min | 24.3 min | 27.8 min |
| Changes per trip | 1.69 | 2.28 | 1.01 |
| Pairs reachable | 100% | 100% | 46% |

*Caption:* Weights: cov 0.20 · int 0.10 · ext 0.10 · vul 0.20 · rob 0.20 · red 0.20. Robustness is a mean over 30 draws, SD 0.090 / 0.037 / 0.023. Z_user is a total, not an average, so it does not compare across cities; the three rows under it do.

**Script:**

What we did. We scored the existing network on every objective, using the same fitness code the optimiser will use rather than writing a second version of it. Objective three compares optimised networks against this column, so if the two were scored by different code the comparison would mean nothing.

Three rows are in bold because they are the three objectives. Everything indented under one is a part of it.

Z_efficiency is the structural one: six measures blended into a single score between nought and one. Coverage is the share of road jeepneys are allowed on that actually carries a route. Internal connectivity asks whether routes meet each other often enough to transfer between; external connectivity whether they touch the city's transport amenities. Vulnerability is how much of the network survives when you knock out its busiest stops one by one, up to a tenth of them. Robustness is the same test with stops removed at random, averaged over thirty draws. Redundancy is the share of serviced road carrying two routes or more.

One thing to flag there. Redundancy is slide thirteen's duplication counted again as a reward: Manila scores point seven nine because seventy-nine percent of its served road carries more than one route. The objective is currently paying the network for the overlap we opened this section by calling a problem. Worth settling before the runs.

Z_CapEx is the build cost from the capacity slides, carried in as the second objective. Nothing new in it: Manila six hundred ninety-seven million against a two hundred million cap.

Z_user is new, and it is the rider's side. For every pair of stops we take the travel time, add five minutes for each change of vehicle, and weight it by how many people live within five hundred metres of where the trip starts. Then we sum that over every pair. Because it is a total rather than an average the cities are not comparable on that line. Manila's being fifty times Makati's mostly says Manila has four times the stops and more people around each. The three rows under it are the comparable ones: an average trip is nineteen minutes in Makati, twenty-four in Manila, twenty-eight in Taguig.

Taguig's last row is the one to look at. Only forty-six percent of its stop pairs can reach each other, so more than half of all possible trips cannot be made at all, even allowing a walk of two hundred fifty metres between nearby stops. Those pairs are charged the worst journey we saw anywhere in that city, which means most of Taguig's Z_user is that charge rather than real travel. This is slide fifteen's five pieces showing up as rider time, and it is why Taguig riders appear to change vehicles least: there is nowhere to change to.

Read across the three objectives and no city wins on all of them. Manila is the strongest structurally and the worst on both cost and rider time. Makati is the cheapest and the quickest to travel. Taguig is weakest on two of the three. If one network were best at everything there would be no trade-off to optimise, and no need for a Pareto front.

If you ask why coverage looks low: the denominator is every road jeepneys may legally use, residential streets included, because real jeepneys drive down them. Makati has three hundred thirty-six kilometres of that against ninety carrying a route. The same definition has to apply to the baseline and to the optimiser, or objective three compares two different scales.

If you ask about rail, it is already inside Z_user: riders walk to LRT and MRT stations within five hundred metres and ride them. Makati has four in range, Manila sixteen, Taguig none.

---

# Backup slides

Not presented. Kept for the Q&A.

## B1 — Why the route counts changed

Two bugs in route construction, both inflating route length. Found while rebuilding the
network from source.

1. **A route number is reused** — for both directions, and for unrelated routes elsewhere in
   the file. Grouping by number merged them. A route is a **run of consecutive rows** sharing
   a number.
2. **Splicing a stop into the road graph cut only one direction** of a two-way road, so the
   return trip detoured around the block.

| | routes | stops | median forward | median reverse |
|---|---|---|---|---|
| Makati | 50 → 50 | 139 → 138 | 4.55 → 2.90 km | 5.91 → 4.64 km |
| Manila | 174 → **307** | 394 → **556** | 12.79 → 10.53 km | 13.78 → 12.32 km |

Residual forward/reverse asymmetry is genuine road geometry — it tracks the one-way share:

| city | one-way share | forward detour | reverse detour |
|---|---|---|---|
| Taguig | 9.6% | 1.01 | 1.05 |
| Mandaluyong | 21.0% | 1.05 | 1.11 |
| Manila | 22.0% | 1.42 | 1.67 |
| Makati | 31.5% | 1.01 | **1.88** |

Forward detour of 1.01–1.05 in three of four cities confirms the splicing is correct. Manila's
1.42 is the same coarse digitising that gives it a 518 m median stop spacing.

## B2 — The `residential` road class

`FILTER_OPTIONS` in the proposal was `primary, secondary, tertiary, trunk, unclassified`.
Before `residential` was added to the EDA's allowed set, **24% of Makati's route arcs, 20% of
Taguig's and 10% of Manila's** were being dropped as "not allowed" while real jeepneys plainly
drive down them — and it left 1,582 holes in Manila's overlap map alone.

`*_link` classes are still excluded: those are interchange ramps, and a route crossing one
still shows a short break.

**Caveat worth stating if asked about unused road.** Adding `residential` roughly doubles to
triples the "available road" denominator (Makati 336 km, Manila 671 km, Taguig 546 km). So
"only 27% of Makati's available road carries a jeepney" is true but the denominator now
includes every residential street, which no realistic network would cover. The robust finding
on slide 13 is the **stacking**, not the unused share.

## B3 — Haversine vs geodesic

The GA moved from `geopy.distance.geodesic` to a haversine implementation
(`utils.route_utils.haversine`, mean Earth radius 6371.0088 km) in mutate, reverse_routes and
the rail layer. The EDA's `analysis/` still uses geodesic.

Measured on every consecutive-stop gap in all three cities, the two differ by **0.23% to
0.33%** — Makati's median gap is 280.6 m by geodesic and 280.3 m by haversine.

**No EDA finding changes.** Not worth converting the analysis code; worth one sentence in the
manuscript saying the two were compared and the difference is immaterial at city scale.

## B4 — The boarding-rate assumption

Rule 3 needs a number we cannot measure: the share of a stop's catchment that boards there in
the peak hour. We use 5%. PHP million:

| rate | Makati | Manila | Taguig |
|---|---|---|---|
| 2% | 70 | 301 | 61 |
| **5%** | **74** | **387** | **100** |
| 10% | 103 | 525 | 161 |
| 20% | 158 | 754 | 237 |

A single unmeasured assumption moves Manila by 2.5×. Rule 3 is the most defensible in
principle and the least certain in practice — both halves are worth saying.

Also: configured `STOP_SIZES` middle value is **40.5 m²** (13.5 m × 3 m), which is not one of the
eleven sizes in the Singapore table. Needs reconciling.

## B4b — Which IRSG run slide 20 quotes

`derived_stop_coords` now rebuilds the run tag from config —
`make_run_tag(WALKING_DISTANCES[WD_TO_USE], STOP_MIN, N_ROUTES[city], N_NETWORKS)` — and reads
`{city}_stops_w750_s20_r{n}_n100.pkl`, falling back to the untagged name only if that is
absent. It therefore follows the group's re-runs automatically.

This was reading a stale pool before. IRSG leaves older parameter sets on disk and the
untagged `{city}_stops.pkl` is simply whatever was written last: Manila's untagged file has
**4,132** candidates against **4,129** in the current settings, and Mandaluyong's 716 against
718. Small differences, but quoting a pool nobody generates against any more is the kind of
thing that is hard to explain afterwards.

**Taguig became available in the process** — it has a pool under the tagged name
(`Taguig_stops_w750_s20_r18_n100.pkl`, 2,028 candidates) but never had an untagged one, so
the old code could not see it at all.

**Makati is currently unreadable** — see the open defects below.

## B5 — Data provenance

- **Makati, Manila routes:** inherited from a previous group, re-derived from the raw Sakay
  WKT exports in `data/jeepney_routes/Original Data/`.
- **Taguig routes:** manually copied from Sakay.ph by this group.
- **Amenity points:** `data/amenity_maps` submodule, now at `02fe154`. All four cities carry
  the same lowercase tags there (residential / institutional / industrial / commercial /
  miscellaneous / transportation), so the `transportation` count read for external
  connectivity means the same thing in each. Counts: Makati 119, Manila 507, Taguig 570.
  Original Jeepney Routes.ipynb still quotes 111 / 464 / 45 from an older snapshot — the two
  have to come from one source or the baseline and an optimised network are scored on
  different denominators.
- Taguig's amenity points were a **16-point stub** until the submodule was updated; the real
  file has 197,980 points, 570 of them transportation. This moved Taguig's external
  connectivity from 0.063 to 0.438. Any Taguig figure predating that is wrong.

---

## What changed since the last version of these slides

Recomputed 2026-11-23 after pulling 33 commits. **Do not reuse the older figures.**

| | was | now | why |
|---|---|---|---|
| Serviced road, Makati | 67.2 km | **90.7 km** | `residential` added to allowed roads |
| Serviced road, Manila | 242.8 km | **326.8 km** | same |
| Serviced road, Taguig | 76.9 km | **90.3 km** | same |
| 3+ routes, Manila | 68% | **62%** | same (larger denominator) |
| Mean routes/arc, Manila | 12.6 | **10.6** | same |
| Max routes, Taguig | 6 | **8** | same |
| Generator stop spacing floor | 500 m | **750 m** | `WD_TO_USE = 1` |
| Share of Makati gaps below floor | 83% | **94.0%** | floor moved to 750 m |
| Coverage, Makati | 0.392 | **0.218** | `residential` tripled the allowed-road denominator |
| Coverage, Manila | 0.643 | **0.398** | same |
| Coverage, Taguig | 0.345 | **0.136** | same |
| Z_efficiency, Makati | 0.573 | **0.526** | coverage is 20% of the weighted score |
| Z_efficiency, Manila | 0.693 | **0.636** | same |
| Z_efficiency, Taguig | 0.447 | **0.406** | same |
| Redundancy, Makati | 0.655 | **0.598** | same denominator change |
| Z_user | not implemented | **4.6 / 233.7 / 9.8 B person-min** | return shape settled, `fitness.py` |
| Z_user reach, Taguig | — | **46.4%** | 6,250 of 11,664 stop pairs unreachable |
| Makati candidate pool | unreadable | **1,779 stops** | IRSG re-saved the right object upstream |
| Manila candidate pool | 4,140 | **4,129** | current IRSG run |
| Catchment radius | our recommendation | **`CATCHMENT_RADIUS_M` in config** | adopted |

**Unchanged:** reach by radius, catchment overlap factors, degree-vs-catchment correlations,
CapEx under all three rules, the budget verdict, stop-spacing medians, the stop-basis table,
internal/external connectivity, vulnerability, robustness.

**The coverage drop is a denominator change, not a regression.** Coverage is serviced road
over allowed road. Adding `residential` roughly doubled-to-tripled the denominator (Makati
136 → 336 km, Manila 318 → 671 km, Taguig 180 → 546 km) while serviced road grew far less.
The networks did not get worse; the yardstick got longer. Worth deciding as a group whether
`residential` belongs in the coverage denominator at all — it is clearly right for *route
construction*, which is why it was added, but it may be too generous as a measure of what a
jeepney network ought to cover. **Whatever is chosen must be the same for the baseline and
for the GA**, or Objective 3 compares two different scales.

---

## Repo fixes this pull required

The pull broke the EDA outright; these were needed to make it run again.

1. **`data/original_jeepney_routes` → `data/jeepney_routes` submodule.** The built network
   pickles lived in its `Saved Networks/` folder and were deleted in `8574552`. Recovered from
   git history into **`data/original_network/`** — outside the submodule, since they are build
   artefacts of this repo rather than shared raw data. `ORIGINAL_DIR` repointed.
2. **Amenity submodule replaced** (`manila-makati-taguig-amenity-maps` →
   `metro-manila-amenity-maps`) and its layout flattened: `Jacob-Group/<City> City/` →
   `<City> City/`. `point_sources` updated.
3. **Taguig's route CSV** moved to `data/jeepney_routes/Taguig_routes.csv`.
4. **Taguig's amenity file was renamed again** by the `02fe154` submodule bump, from
   `taguig_point.geojson` to `taguig_amenities_points.csv.zip` — a zipped CSV with WKT in a
   `geometry` column, where `gpd.read_file` returns the rows with no geometry at all.
   `read_city_points` now reads a CSV through pandas and builds the geometry from that
   column, and `POINT_SOURCES` lists all three names it has had, newest first. The counts
   are unchanged (570 transportation points either way), so no figure moved; without the
   fix the EDA simply stops at Taguig.
5. **`fitness_user_cost` returned two different shapes** — a bare float on the normal path,
   `(float, dict)` on one failure path — so `baseline.py` could not call it and Z_user stayed
   blank. Every exit now goes through one local `out()` helper: the scalar by default, which
   is what `fitness_score` appends and what NSGA ranks, and `(scalar, details)` only when the
   caller passes `return_details=True`. **The GA path is byte-for-byte unchanged**; the only
   caller using the new keyword is `analysis/baseline.py`. The diagnostics dict that was
   commented out mid-refactor is live again, and `n_jeep_od` — which it referenced but nothing
   defined — is now counted before the rail stations are appended to the OD set.

Upstream also changed `FIGURE_DIR` to `../plots/EDA` (capitalised). Harmless on Windows,
breaks on Linux — worth settling on one spelling.

---

## Figure and table assets

In `plots/eda/`, regenerated 2026-11-23 against the pulled code:

| file | slide | state |
|---|---|---|
| `overlap_map_manila.png` | 13 | current |
| `catchment_radius.png` | 14 | current |
| `overlap_map_taguig.png` | 15 | current |
| `capex_options.png` | 17 | current |
| `degree_vs_catchment.png` | backup only — slide 18 uses a table instead | current |
| `stop_spacing.png` | 19 | current |
| `overlap_map_makati.png` | backup | current |
| `overlap_profile.png` | backup — alternative to slide 13's map | current |
| `stop_basis.png` | **not used** | ⚠️ **stale** — still the Makati-only pool, 138 against 1,779. Slide 20 uses a table instead. Regenerate or delete. |

`plots/slides/network_overview_table.png` — the counts table. Styled for the **old** THS-1
look (Anton/`#D1442F`), so it does not match the THS-2 deck. Regenerate it in League Spartan
with the `#DD6B6C` accent before using it.

**The slide 12 flowchart is drawn** in the built deck as four accent-ruled input boxes
feeding one build step. It was the one asset the adviser asked for by name and the only one
that could not come out of the notebook.

⚠️ **`plots/slides/` also contains `slide3_*`, `slide5_*`, `slide6_*` and `slide8_*` table
images from another session, dated 11-14.** Those were numbered for the previous 8-slide
structure, which this document replaces, and they predate the recomputation — so their numbers
are stale as well as misnumbered. Left untouched rather than overwritten. They need either
regenerating against the numbers here or deleting.

---

## Open defects — for the group, not the slides

Found while making the EDA run again after the pull. All sit in work other people have in
flight, and none is fixed here except the Z_user return shape noted above, which the EDA
could not run without.

**Closed by the 2026-11-24 pull.** `Makati_stops_w750_s20_r28_n100.pkl` used to hold a list
of 100 `Network`s instead of the stop graph, because `IRSG.ipynb` reused one `file_path`
variable across two saves. Upstream re-saved it: all four cities now load, Makati with 1,779
candidates, so slide 20 quotes it. The underlying cause is still there — cell 14 sets one
`file_path`, cell 16 reassigns it — so it will recur if those cells are run out of order
again. Giving each save its own variable would settle it.

1. **`INVALID_NETWORK_COST = 1e12` has less headroom than its own comment claims.**
   `config.py:44` says Makati measures ~6e9 and Manila "an order of magnitude above",
   leaving three decades. Measured, Manila's existing network is 2.34e11 — the sentinel is
   only 4.3x above a *valid* network's cost, so a bad-but-scoreable Manila network can rank
   worse than an unscoreable one. Raising it to 1e14 costs nothing; the comment should carry
   the measured figures either way.

2. **Manila's `Z_CapEx` reads PHP 796,654,000 in
   `data/eda/original_network_baseline.csv`, against PHP 697 M on slides 17 and 21.** The
   difference is exactly `fitness.py:120`'s `fixed_penalty = 100000000`, which is folded into
   the returned CapEx instead of only steering selection. The slides show the real cost. If a
   panelist opens the CSV this is the discrepancy they find, so it is worth fixing before the
   demo rather than explaining live.

3. **`schema.py` `RunState.from_checkpoint` passes `population=` to a field named
   `network_population`** — resuming from a checkpoint raises. Not EDA, but it will bite
   during the runs.

4. **NSGA cell 4 hardcodes `ru.make_run_tag(HYPERPARAMETERS["walk_distance"], 20, 10, 100)`**
   — the `10` is Mandaluyong's route count, so the tag is wrong for every other city. It
   currently masks defect 0.

Also minor: upstream set `FIGURE_DIR = ../plots/EDA` while the folder on disk is
`plots/eda`. Same folder on Windows, a different one on Linux. Worth settling on one spelling
before someone runs this on the lab server.

---

## Likely panel questions

**"Where does ridership come from?"**
It does not. No ridership data exists for jeepneys. Demand is estimated from residential
population within 500 m, apportioned across stops — the limitation declared in the proposal.

**"Your proposal used Taft. Now you say Quiapo."**
Taft is still heavily duplicated, just not the worst. The proposal picked it from a photograph;
this is the first time anyone measured. Carlos Palanca carries 107 routes.

**"If the existing network is over budget, what is the optimiser for?"**
The cap is a configuration value we chose, not a real constraint — slide 17 is the argument for
setting it per city from measured cost. The unconstrained run is already Objective 3's second
comparison point.

**"Why Singapore's design criteria for Philippine stops?"**
It is a published table mapping passengers per hour to shelter floor area, and we found no
local equivalent. We use it as a basis for the *relationship* — more passengers, more
shelter — not for its absolute figures. The cost per square metre is local PUV shelter data.

**"You changed the route counts since the proposal. Which is right?"**
The current ones. See B1.

**"Why only three cities?"**
Those are the three in the proposal's scope. Mandaluyong is built and loadable but not presented.

**"Where does the basemap come from?"**
OpenStreetMap — same source as our road network, same render as the QGIS figures in section 02.
Attribution is in the corner of every map. Background only; no analysis uses the tiles.

**"Should you wait for the CZC and IRSG rerun?"**
No. The candidate pool is the CZC-tagged road nodes and it is stable across runs — Manila came
out 4,132 / 4,138 / 4,140 / 4,129 across four builds, Mandaluyong 716 / 718. Walking distance changes
which candidates get *used*, not which exist. Only a CZC rerun could move slide 20.
