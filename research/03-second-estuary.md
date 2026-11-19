# Second estuary for the chlorophyll warning model (scouted 2026-11-17)

Drafted with Claude (AI) as a read-only scout. Nothing was downloaded. Every claim below says whether I opened the source myself (VERIFIED) or not (UNVERIFIED).

## Summary (10 lines)
1. **First pick: five USGS sensors in Long Island waters (New York).** Hog Island Channel at Island Park is the long one (daily data from 2013-07-19). Reynolds Channel at Point Lookout and the Peconic River at Riverhead start in 2017. Shelter Island Sound starts in 2022 and West Harbor at Oyster Bay in 2023. (VERIFIED, USGS catalogue, today.)
2. Why: USGS data is public domain, needs no account or key, and a free API works right now (VERIFIED). It is tiny (a few MB), and it is in the New York area.
3. Size of the test: about 12,300 station-days of daily-mean chlorophyll (VERIFIED counts, summed by me). A rough guess is 300 to 600 threshold-crossing events. That guess is UNVERIFIED and must be computed on the real data. The old test had [redacted: from the restricted Bay file].
4. Weak spots: only 3 stations have 9 or more years; the sensors read fluorescence, not lab chlorophyll; the water is narrow tidal channels, so satellite pixels may be mixed with land. Sentinel-3 (300 m) will not work here; Sentinel-2 (10 m) might.
5. **Backup: NOAA Chesapeake Bay buoys (CBIBS).** Open main-stem Bay, so satellites can see it. The download page offers 2007 to 2026 (VERIFIED), and the data feed lists a chlorophyll field (VERIFIED). But I could not find written terms, which stations have chlorophyll in which years is unchecked, and the API wants a key by email. So it is a backup, not the first pick.
6. Third: NERRS SWMP (NOAA reserves). Long, 15-minute, with weather on site, but chlorophyll is an "optional" sensor, you must register a fixed IP address, and CDMO says data "should not be archived by outside sources for distribution" (VERIFIED). That blocks republishing.
7. **Ruled out as a public source: Maryland Eyes on the Bay.** Best record I found (about 15 stations, 2003 to 2026, 15-minute chlorophyll), but its policy forbids releasing the raw data to third parties without written permission (VERIFIED). Fine for private checks, not for a public repo.
8. Neuse/ModMon is boat sampling every two weeks, not continuous (VERIFIED). Out.
9. **Not checked** because the Brave search cap hit 30/30: Narragansett Bay, Long Island Sound buoys, Tampa Bay, Indian River Lagoon, NERACOOS, Puget Sound, Columbia River (CMOP), Europe/Australia. Do not read "not listed" as "not good".
10. Next step I would take: pull the five USGS series, count real p90 crossings per station, and only then decide whether this place is big enough. Needs Jayden's yes to start only if the plan says so; downloads from this open API are free and allowed under Rule 3 (log in `SOURCES.md`).

## Comparison table
Scores: Y = meets, P = partly, N = fails, ? = could not confirm. "V" = I opened the source today; "U" = unverified.

| Candidate | 1 Continuous chl at fixed stations | 2 Years / stations | 3 Co-located data | 4 Open terms and access | 5 Size | 6 Blooms / studies | 7 Satellite-visible | Link | Status |
|---|---|---|---|---|---|---|---|---|---|
| **USGS Long Island (NY): 01311143, 01310740, 01304562, 01304650, 01303152** | Y. Daily mean/max/min series; 6-minute readings on the live page for West Harbor. | 13.3, 9.5, 9.1, 4.2, 3.0 years. 5 stations. | P. West Harbor page lists temp, conductance, pH, DO, chlorophyll, phycocyanin, phycoerythrin, tide height. Other four stations not read. Weather and river flow are not at these sites. | Y. Public domain. No account, no key. | Tiny | P. Gobler et al. studies of NY estuary blooms exist; no forecasting paper found. | P/N. Narrow channels; S2 maybe, S3 no. | https://waterservices.usgs.gov/nwis/site/?format=rdb&sites=01311143,01310740,01304562,01304650,01303152&parameterCd=32316&seriesCatalogOutput=true | V |
| NOAA CBIBS buoys (Chesapeake Bay) | Y?. Chlorophyll field in the API list; stations AN, GR, J, FL, N, PL, S, SN, SR, UP, YS. Which have chlorophyll, and when, not checked. | Download form offers 2007 to 2026; 6 buoys live in 2026, 5+ retired. | Y. Wind, gusts, air temp, pressure, waves, currents, salinity, turbidity, oxygen, nitrate listed. | P. Terms not found. API needs a key from NOAA by email; web download form shows no login. | Small to medium (U) | Y. Chesapeake has many studies (see below). | Y. Open Bay. | https://buoybay.noaa.gov/data/api | V (pages), U (chlorophyll coverage, terms) |
| NERRS SWMP via CDMO | P. ChlFluor is "optional"; 15-minute; which reserves log it, not checked. | Reserves since the 1990s to 2000s (U). 4 water stations per reserve. | Y. Same reserve has wind, PAR, rain, air temp. | N/P. Page says "public information", but you must request authorisation with a static IP. Not to be archived for distribution. | Medium (U) | Y (many papers, U). | Mixed. | https://cdmo.baruch.sc.edu/webservices.cfm | V (rules), U (coverage) |
| Maryland DNR Eyes on the Bay (continuous) | Y. 15-minute chlorophyll fluorescence, 1 m depth. | About 20 stations with data to 2026; long ones: JUG 2003, OPC 2003, SPS 2004, SUS 2007, LMN 2006, SGC 2006, MSC 2013. | Partial (7 water parameters; no flow, no weather). | **N. Raw data may not be passed to third parties without written permission.** Web query form, no account. | Small | Y. | Tidal rivers/creeks; mixed. | https://eyesonthebay.dnr.maryland.gov/contmon/ContMon.cfm | V |
| HRECOS (Hudson River, NY) | P. 15-minute; chlorophyll at Port of Albany seen on USGS page (2025). Other stations not checked. | Collecting since 2008; 15 stations (V per site). Before 2026 from USGS; 2026 on from HRECOS portal, 60-day request cap. | Y (weather stations). | P. "Anyone can access", attribution wanted. Form-based. | Small | ? | River; narrow at Albany, wider south. | https://hrecos.org/request-data/ | V (site), U (chlorophyll years) |
| USGS in other states (NJ, MD, DE, CT, RI, MA, NC, SC, FL, GA, CA, ME) | Site query for codes 32316, 32318, 32319 returned 0 sites (MD, DE, CT, RI, MA, NC, SC, FL, GA, CA, ME) or only non-estuary rivers (NJ). | n/a | n/a | Y (USGS). | n/a | n/a | n/a | USGS site service (query run by command line) | V for the count; U that no other code is used |
| USGS Louisiana (07380249, 07380260) | Y but short | 2023 to 2026 | ? | Y | tiny | ? | ? | same service | V counts, too short |
| Neuse Estuary ModMon (NC) | **N.** Boat sampling every 2 weeks, plus ferry runs. | Long, but not continuous. | n/a | Data by e-mail request. | n/a | Y | n/a | https://paerllab.web.unc.edu/projects/modmon/ | V |
| Narragansett Bay, LISICOS, NJDEP, Tampa Bay, Indian River Lagoon, NERACOOS, Puget Sound, CMOP SATURN, Europe/Australia | Not checked (search cap reached; LISICOS host did not resolve; SATURN server returned 502). | | | | | | | | **U** |

## Top 3 in detail

### 1. USGS Long Island estuary sensors (first pick)
**Stations and years (VERIFIED, USGS site-service catalogue, 2026-11-17; daily series begin and end dates):**
- 01311143 Hog Island Channel at Island Park NY, 2013-07-19 to 2026-11-17, about 4,109 daily means.
- 01310740 Reynolds Channel at Point Lookout NY, 2017-05-20 to 2026-11-17, about 2,989.
- 01304562 Peconic River at County Hwy 105 at Riverhead NY, 2017-10-03 to 2026-11-17, about 2,979.
- 01304650 Shelter Island Sound at Shelter Island NY, 2022-09-20 to 2026-11-17, about 1,149.
- 01303152 West Harbor at Oyster Bay NWR at Bayville NY, 2023-11-18 to 2026-11-17, about 1,042.
(For the first three of these, the catalogue listed three statistic rows without codes; I assumed the third row is the mean. For Hog Island and Shelter Island the codes were printed: 00001 = max, 00002 = min, 00003 = mean. Check this when you pull data.) Total about 12,300 station-days.

**Exact download route (no account, no key; the two calls below were tested today with tiny requests only):**
1. Confirm stations and dates: `https://waterservices.usgs.gov/nwis/site/?format=rdb&sites=01311143,01310740,01304562,01304650,01303152&parameterCd=32316&seriesCatalogOutput=true` (parameter 32316 = chlorophyll fluorescence, ug/L). Note: the response is about 60,000 characters because it lists every series.
2. Daily values, new API (worked today): `https://api.waterdata.usgs.gov/ogcapi/v0/collections/daily/items?f=csv&monitoring_location_id=USGS-01311143&parameter_code=32316&limit=1000`, then follow the `next` link. The reply carries `statistic_id` (00003 = mean), `approval_status` and `time`. Results are not sorted by date, so sort after download. The reply links point to `/v1/`, so use v1 for future code.
3. Daily values, old API (also worked today, but USGS is moving away from it): `https://waterservices.usgs.gov/nwis/dv/?format=rdb&sites=01311143&parameterCd=32316&statCd=00003&startDT=2013-07-01&endDT=2026-11-17`. NOTE: my test sample used statCd=00001, which is the daily MAXIMUM. Use 00003 for the mean.
4. 15-minute or 6-minute data: the catalogue lists an instantaneous ("uv") series for each station. How far back it is served at full resolution is UNVERIFIED. Test with one month before planning around it.
5. Same-site temperature, conductance, oxygen, turbidity, tide height: query the same site with other parameter codes. Which codes each of the five sites has was NOT checked, except West Harbor's list.

**Terms (VERIFIED, https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits):** "considered to be in the U.S. Public Domain." They ask for credit ("Credit: U.S. Geological Survey"). Some non-USGS photos on that site are copyrighted; this does not apply to the data, but check each site's cooperator note.
**Expected size:** a few MB for daily data. 15-minute data for 5 stations would be roughly 100 MB to 300 MB at most (my arithmetic; UNVERIFIED). Well under 10 GB.
**What could go wrong:**
- Only three stations have 9 or more years, so "many test years" means about 9 to 13, not 20.
- Fluorescence sensors drift, foul and get swapped. A jump in the series may be a sensor change, not a bloom. This is the same worry as [redacted: from the restricted Bay file].
- Narrow channels mean tide moves water past the sensor. A "bloom" may be a different water mass.
- Satellite: Sentinel-3 pixels (300 m) will include land. Sentinel-2 (10 m) may work in Reynolds and Hog Island channels; I did not measure channel widths (UNVERIFIED).
- Recent values are provisional and may change.
- Event count is a guess. A threshold at the 90th percentile with daily data and persistent blooms gives far fewer "new crossings" than days above threshold. Count it before committing.
- The old NWIS service may be retired; the new API is the safer choice.
- No weather or river-flow series at the sensors. You would add NOAA or NY Mesonet separately (not checked).

### 2. NOAA CBIBS buoys, Chesapeake Bay (backup)
**What I saw (VERIFIED):** the download form at https://buoybay.noaa.gov/data/data-download lists stations AN, FL, GR, J, N, PL, S, SN, SR, UP, YS, years 2007 to 2026, and types "Ocean" and "Met". The API page https://buoybay.noaa.gov/data/api lists `mass_concentration_of_chlorophyll_in_sea_water`, turbidity, salinity, oxygen, nitrate, wind and waves, at 6-minute spacing. QA codes are included.
**Download route:** (a) web form: pick station, year(s), type, and download. No login shown; I did not run it. (b) API: `https://mw.buoybay.noaa.gov/api/v1/json/query/AN?key=<key>&sd=<start>&ed=<end>&var=mass_concentration_of_chlorophyll_in_sea_water`. A key is needed. The page prints a "testing key" but says it may change and is for testing only; I did not use it. Asking for a key means sending NOAA an email, which needs Jayden's yes.
**Terms:** not found. The site's Disclaimer page only covers external links (VERIFIED). NOAA data are usually open, but I did not find it written for this system. Ask the NOAA Chesapeake Bay Office before publishing raw data.
**Size:** small (a few hundred MB at most, UNVERIFIED).
**What could go wrong:** chlorophyll may be missing at some stations or years; buoys are pulled in winter and moved; the sensor is not lab-calibrated; terms unwritten.

### 3. NERRS SWMP (reserves; includes the Hudson River, Jacques Cousteau NJ and Chesapeake Bay VA reserves, UNVERIFIED which have chlorophyll)
**Route (VERIFIED, https://cdmo.baruch.sc.edu/webservices.cfm):** SOAP web service at `http://cdmo.baruch.sc.edu/webservices2/requests.cfc?wsdl`. Functions `exportStationCodesXMLNew` (lists stations and parameters), `exportAllParamsDateRangeXMLNew` (max 1,000 records per call), `exportSingleParamXMLNew`. Needs prior authorisation and a static IP. The yearly "authenticated" files page (https://cdmo.baruch.sc.edu/dges/) did not show its file list to my fetch.
**Terms (VERIFIED):** "Data ... is considered public information" (https://www.nerrsdata.org/data/policy.cfm), credit to the site required. But the web-services page says outside parties should not archive the data for distribution, because "the most complete and up to date dataset" lives at CDMO. A public repo with copies of the data would go against that. A repo with code and a download script would not.
**Parameters:** ChlFluor (RFU, optional), Temp, Sal, DO, Turb, Depth, plus weather: wind, PAR, rain, air temp (VERIFIED, https://www.nerrsdata.org/data/parameters.cfm). Fluorescence in RFU, not ug/L.
**What could go wrong:** the IP registration form is a "form" (needs Jayden's yes); long 15-minute files make 100 to 1,000 calls; coverage unknown until registered.

## Published studies to compare against
**For the first pick (Long Island):** I found no forecasting paper on these USGS stations (UNVERIFIED; search was capped).
- Gobler, Burson, Koch, Tang, Mulholland (2012). Nitrogen and harmful algal blooms of Cochlodinium polykrikoides in New York estuaries. Harmful Algae. DOI 10.1016/j.hal.2012.03.001. Opened the record via Crossref today; I did not read the paper. About causes, not forecasting.
- Griffith, Shumway, Gobler (2018). Shellfish deaths in Cochlodinium (Margalefidinium) blooms. Estuaries and Coasts. DOI 10.1007/s12237-018-0445-0. Crossref record only.

**For the backup (Chesapeake Bay):**
- Gupta and Gupta (2025). Time series forecasting of chlorophyll-a in the Chesapeake Bay. Scientific Reports 15:30877. https://www.nature.com/articles/s41598-025-16352-3 (opened, read). Weekly satellite chlorophyll 1997 to 2020, three Bay regions; LSTM beat ARIMA and TBATS (RMSE 0.121, 0.155, 0.199 mg/m3). It forecasts amounts weekly, not threshold crossings, and says its models miss extreme peaks. Open Access, CC BY-NC-ND.
- Lin, Liu, Song, Liu, Yin, Hall (2023). Temporal prediction of coastal water quality based on environmental factors with machine learning. J. Mar. Sci. Eng. 11(8):1608. DOI 10.3390/jmse11081608. Crossref record opened; I did not read the paper. Gupta and Gupta say it covers the Neuse River Estuary and a Pacific pier site and found wavelet-filtered LSTM and BPNN most robust (secondhand, UNVERIFIED).
- Remote Sensing 18(11):1736 (2026), "Comparative Evaluation of Machine Learning Models for Satellite Chlorophyll-a Gap Reconstruction in the Chesapeake Bay". https://www.mdpi.com/2072-4292/18/11/1736. Seen as a search snippet only (UNVERIFIED beyond the title).

## What I could not do (be careful with these)
- Brave search hit its session cap (30/30) mid-way; I stopped using it and did not switch to another search tool. The unchecked list is in row 9 of the summary.
- The Maryland data-use PDF was downloaded to my scratchpad to read it (one small policy document, not a dataset).
- USGS site-catalogue calls were made from the command line (small metadata only) because the Scrapling output was too large to read directly.

## Sources opened today (2026-11-17)
- https://cdmo.baruch.sc.edu/webservices.cfm, https://www.nerrsdata.org/data/policy.cfm, https://www.nerrsdata.org/data/parameters.cfm
- https://eyesonthebay.dnr.maryland.gov/contmon/ContMon.cfm, .../contmon/ContinuousMonitoring.cfm, .../eyesonthebay/documents/EyesOnTheBay_datause.pdf
- https://hrecos.org/request-data/
- https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits
- https://waterservices.usgs.gov/nwis/site/ (several queries), https://waterservices.usgs.gov/nwis/dv/ (one 11-day sample), https://api.waterdata.usgs.gov/ogcapi/v0/collections/daily/items (2 records)
- https://buoybay.noaa.gov/ (home, /data/data-download, /data/parameters-measured, /data/api, /disclaimer)
- https://paerllab.web.unc.edu/projects/modmon/
- https://www.nature.com/articles/s41598-025-16352-3
- https://api.crossref.org/works (two lookups)
