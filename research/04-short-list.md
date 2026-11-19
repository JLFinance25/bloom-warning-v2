# Short list: what goes into the redo, and what stays out (2026-11-17)

Claude's picks after three scout reports (`01`, `02`, `03` in this folder) and Claude's own checks. Each "checked"
below means Claude opened the source itself on 2026-11-17. Everything else is the scouts' word and is marked.

## Second place: five USGS sensors in Long Island, New York waters
Checked in the USGS public catalogue (`waterservices.usgs.gov/nwis/site`, series catalogue, daily values):

| USGS station | Where | Daily-mean chlorophyll (code 32316) | Days |
|---|---|---|---|
| 01311143 | Hog Island Channel at Island Park | 2013-07-19 to 2026-11-16 | 4,109 |
| 01310740 | Reynolds Channel at Point Lookout | 2017-05-20 to 2026-11-16 | 2,989 |
| 01304562 | Peconic River at Riverhead | 2017-10-03 to 2026-11-16 | 2,979 |
| 01304650 | Shelter Island Sound at Shelter Island | 2022-09-20 to 2026-11-16 | 1,149 |
| 01303152 | West Harbor at Oyster Bay (Bayville) | 2023-11-18 to 2026-11-16 | 1,042 |

Same stations also log water temperature, salt, dissolved oxygen, pH, cloudiness of the water and tide height
(checked in the same catalogue). About 12,300 station-days of chlorophyll in all.

Why this one: USGS data is public domain (scout's quote; standard USGS policy), needs no account or key, is a
few megabytes, and updates daily. Weak spots: only three stations have nine years or
more; the sensors read fluorescence (a light signal that stands in for chlorophyll); recent USGS data is marked
provisional until USGS approves it.

Not chosen: Maryland "Eyes on the Bay" (best record the scout found, but its policy forbids passing raw data on
without written permission); NOAA reserve network (must not be archived for redistribution; needs a registered
IP address); Chesapeake buoys (terms not found, key by email). Not checked at all, because the search tool hit
its daily cap: Narragansett Bay, Long Island Sound buoys, Tampa Bay, Indian River Lagoon, Gulf of Maine, Puget
Sound, Columbia River, Europe, Australia. "Not checked" does not mean "worse".

## New inputs, in the order they get tested
1. **More from the sensors each station already has.** Daily peak chlorophyll, how fast chlorophyll is rising,
   days since the last high day, the daily swing in dissolved oxygen (algae make oxygen by day and use it by
   night, so a growing population widens the swing), and changes in temperature, salt and water cloudiness.
   Physical reason: these describe the algae at that station today. Cost: none, the data is in hand.
2. **Spring and neap tides from the moon's phase.** Physical reason: South Bay blooms start in weak (neap)
   tides, when the water stops mixing (Cloern 1985 and Nardelli 2026, opened by the scout, not by Claude). The
   moon's phase is known years ahead, so it is a fair input for the next three days. Cost: none.
3. **Neighbouring stations today.** Physical reason: blooms move with the water and shallow areas seed channels
   (scout, snippet only). Differs by station. Cost: none.
4. **Tree models** (many small yes/no decision charts, averaged). Reason: the satellite competition's winners all
   used them (Claude read the winners' page). They also pick up "this input matters only at that station".
5. **Satellite water colour near each station (Sentinel-2).** Checked: free, no account, images through
   2026-11-14, small windows can be read. Risks: clouds and fog (scout: about a third of images mostly clear),
   narrow sloughs only a few pixels wide, and the colour index is unproven in muddy water.
6. **Weather at each station's own location** instead of one Bay-wide number.

## Left out, and why
- Delta outflow and ocean upwelling: one value for the whole Bay, and both arrive weeks to a year late.
- Coarse satellites (300 m and up): pixels are wider than the sloughs.
- Creek flow: live and free (scout), but matching creeks to stations would be guesswork tonight.
- Wastewater plant loads: monthly and months late (scout).
- Any source that needs an account or key.

## Open item for Jayden
SFEI's sensor dataset has a public catalogue record (checked: DataCite, DOI `10.6073/pasta/69b73427d4f9021e2fbcf7b89bbfbf23`,
"San Francisco Bay High-frequency Water Quality Sensor Data", published 2026, EDI package `edi.2260.1`). The
scout reports it covers 2013 to 2021 at eleven stations with an open license, from search snippets only:
UNVERIFIED. The page shows a human check to tools, so a person must open it.
