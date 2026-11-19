# Prior work scout: predicting algal blooms and high chlorophyll

Date opened for all sources: 2026-11-17. Drafted by Claude (AI) as a research scout; not yet checked by Jayden.

**How sure each claim is.** Every source line ends in one of three tags:
- **[OPENED]** I read the page or PDF text myself.
- **[SNIPPET]** I only saw a search-result excerpt of the page. Treat as UNVERIFIED until opened.
- **[INDEX]** I saw the paper's abstract in the Firecrawl research index, not the journal page. UNVERIFIED beyond the abstract.

Pages that blocked me (CAPTCHA or bot check, not bypassed): PubMed (two abstract pages, reCAPTCHA), PMC (cookie/bot wall), SFEI data page (HTTP 403). Marked BLOCKED below. No account, form, login or download of data was used. Two PDFs (Beckmann 2025, Anderson 2016) were saved to the scratchpad only to read them.

## 10-line summary

1. The competition is almost surely **DrivenData "Tick Tick Bloom"** (NASA-backed, Feb 2023, 1,377 joined, $30,000 prizes). Your memory was right. [OPENED]
2. It was **detection, not forecasting**: estimate cyanobacteria severity (levels 1 to 5) in small inland lakes and reservoirs on the day a water sample was taken, from satellite color, weather and elevation. Test locations were never seen in training. [OPENED]
3. Winners used **gradient-boosted trees on simple summary numbers** (mean red/green/blue of the water pixels, temperature, humidity), not deep image models. CNNs did badly. [OPENED]
4. Five ideas to copy: (a) region-specific models, and drop satellite data where it is poor; (b) cut each satellite image down to water pixels first; (c) use temperature and humidity-type features, skip wind and rain; (d) average several boosted models; (e) judge the model on places and years it never saw.
5. Idea 6 to copy: always show the **persistence rule** ("tomorrow equals today") next to every model. The only forecasting paper I opened that did this found a random forest beat it by about 16% on one error measure, and a neural net never reliably beat it.
6. For San Francisco Bay, the literature names **stratification (neap tides, river outflow), light and turbidity, wind, residence time, grazing by bottom clams, temperature and day length**. Spring-neap tide phase is the most station-measurable idea and is cheap to compute.
7. Trap 1: **leakage**. Random splits, interpolating sparse data to daily, and processing across years all inflate scores. A 2026 critique says so directly. [SNIPPET]
8. Trap 2: **persistence is a hidden baseline**. Several papers feed in the last chlorophyll value and then credit the model for "predicting" it. Chesapeake LSTM paper compared only to ARIMA/TBATS (no persistence). [OPENED]
9. Trap 3: **satellite chlorophyll is unreliable in turbid shallow water** and during the 2022 bloom the standard SF Bay algorithms failed; a refit red-edge algorithm worked. Clouds and fog add gaps. [INDEX/SNIPPET]
10. Honest gap: I found **no published short-lead (1 to 3 day) chlorophyll-threshold forecast at fixed estuary sensors that reports skill against persistence**. Our redo may be new ground. UNVERIFIED (absence of evidence after a limited search).

---

## 1. The satellite competition

### 1.1 Tick Tick Bloom: Harmful Algal Bloom Detection Challenge (DrivenData, for NASA)
- Competition home: https://www.drivendata.org/competitions/143/tick-tick-bloom/ [OPENED]
- Problem description page (inside the competition): https://www.drivendata.org/competitions/143/tick-tick-bloom/page/650/ [OPENED]
- About / rules page: https://www.drivendata.org/competitions/143/tick-tick-bloom/page/651/ [OPENED]
- Winners post (14 Apr 2023): https://drivendata.co/blog/tick-tick-bloom-challenge-winners [OPENED]
- Winners' code repo (MIT license): https://github.com/drivendataorg/tick-tick-bloom [OPENED, README only; the three write-up reports sit in the "1st Place", "2nd Place", "3rd Place" folders and I did not open them]
- Archive copy of the winning code: https://zenodo.org/records/8329930 [SNIPPET]
- Benchmark post (LightGBM on satellite colors): https://blog.drivendata.org/blog/tick-tick-bloom-benchmark [SNIPPET, not opened]

**What was predicted.** The severity level (integer 1 to 5) of cyanobacteria (blue-green algae) density at one place and date. Levels come from cell counts per milliliter: level 1 is under 20,000; 2 is 20,000 to under 100,000; 3 is 100,000 to under 1 million; 4 is 1 million to under 10 million; 5 is 10 million or more. Raw density was supplied in training but participants submitted severity only. [OPENED]

**Where.** Small inland lakes, reservoirs and rivers across the continental U.S. (sampling dates back to 2013), grouped into four regions: West, Midwest, South, Northeast. Not estuaries or coasts. [OPENED]

**Labels.** Manual "in situ" water samples counted by many state and federal agencies (the about page lists dozens: state environment departments, EPA, USGS and others). [OPENED]

**Inputs allowed.** Four sources only: Sentinel-2 imagery (required), Landsat 8/9 imagery, NOAA HRRR weather model data (temperature, humidity, wind, precipitation), and Copernicus 30 m elevation. Rule: only data available on or before the sample date. Other external data was not allowed. [OPENED]

**Size.** I did not find a row count for train or test. What I did see: 1,377 people joined, "over 900 submissions", 4 regions. UNVERIFIED beyond that. The winners post calls it "uniquely large and geographically diverse" for cyanobacteria. [OPENED]

**Test design (important).** Each geographic area is entirely in train or entirely in test, so scores measure performance on **unseen locations**. [OPENED]

**Scoring.** Region-averaged RMSE: compute the root-mean-squared error of severity in each of the 4 regions, then average the 4. Winning score about 0.76 (private leaderboard); the simple benchmark's error was more than double. [OPENED]

**How the winners did it** (all from the winners post and repo README, [OPENED]):

| Place | Who | Approach |
|---|---|---|
| 1st | "sheep" (Yang Xu) | Midwest and Northeast: gradient-boosted trees on temperature plus satellite "water color" (mean and 95th-percentile red, green, blue of the water pixels). West and South: no imagery, a nearest-neighbors model on location only, because he judged the data there too noisy or the water bodies too small for 10 to 60 m pixels. Private score 0.7608. |
| 2nd | "apwheele" (Andrew Wheeler) | Three boosted regressors (LightGBM, XGBoost, CatBoost) averaged; features were date, location, elevation, and RGB of the lake area found by k-means segmentation of Sentinel-2. Private 0.7616. |
| 3rd | "karelds" (Raphael Kiminya) | Separate boosted trees for each satellite (Landsat 8, 9, Sentinel) in each region; averaged 10 models; imagery within 200 m of the point and up to 15 days before; temperature and humidity from HRRR for the previous 24 hours. Private 0.7844. |

**Tricks and lessons the organizers and winners stress:**
- Treat regions differently; some data is simply too poor to use.
- Overall color statistics of the water pixels beat deep image models, because the lakes were too small for the pixels.
- CNNs and a U-Net segmentation model were tried by the winner and failed (very high error).
- Temperature, humidity and elevation helped most; precipitation and wind "did not turn out to provide useful modeling information". The 3rd-place winner found elevation overfit the training set and hurt on the test set.
- Cloud masks and a water-pixel mask (Sentinel-2 scene classification band) were used to find "real water".

**Licenses.** The repo is MIT; competition rules require winning solutions to be MIT-licensed. [OPENED]

**What it means for us.** This is a *nowcast on unseen lakes*, a different problem from a 1 to 3 day warning at fixed stations we already have years of data for. Copy the feature craft (water-pixel color stats, temperature, region-specific models, boosted-tree averaging), not the headline score.

**Confidence:** high on facts above; I did not read the write-up PDFs.

### 1.2 Follow-on tool: CyFi (open source)
- https://github.com/drivendataorg/cyfi and https://cyfi.drivendata.org/ [SNIPPET]
- https://drivendata.co/blog/cyfi-small-water-bodies (says Sentinel-2 at 10 to 30 m, lakes under about 250 acres) [SNIPPET]
- Paper: Dorne, Wetstone, Cerquera, Gupta (2024), SciPy Proceedings, https://proceedings.scipy.org/articles/PDHK7238 [SNIPPET]
- One more related paper, a 2025 severity-classification study using the same data: https://www.sciencedirect.com/science/article/abs/pii/S2352938525003532 [SNIPPET]
Not opened; confidence low-to-medium.

### 1.3 Other competitions or benchmarks
- Kaggle "Predicting Algae Blooms": https://www.kaggle.com/c/algaeblooms [SNIPPET]. Its background credits the textbook *Data Mining with R*, so it is probably a small classroom dataset of river algae counts, not satellite. UNVERIFIED; not opened.
- "Amfitrite Inland Waters HAB": 4,698 Sentinel-2 tiles with low/moderate/high labels, listed on https://github.com/satellite-image-deep-learning/datasets [SNIPPET]. Not opened.
- I looked for Zindi, ESA, NOAA and CyAN competitions in one search and found nothing new. UNVERIFIED that none exist. CyAN (NASA/EPA/NOAA/USGS cyanobacteria assessment network) is a data program, not a competition; I did not open its pages.

---

## 2. Short-lead bloom or chlorophyll forecasting in estuaries and coasts

Honest headline: most papers forecast **weekly or monthly** values, many do not report persistence, and few use event thresholds. Order below runs from most to least useful to us.

1. **Beckmann et al. 2025, "Are more data always better? Machine learning forecasting of algae based on long-term observations."** J. Environ. Management 373:123478. https://www.dora.lib4ri.ch/eawag/dload/eawag:33891/PDF/Atton_Beckmann-2024-Are_more_data_always_better--(published_version).pdf [OPENED]
   - Place/target: Blelham Tarn, a small English lake (freshwater, not estuary); chlorophyll-a two weeks ahead.
   - Inputs: 13 fortnightly measures (nutrients, temperature, weather, etc.). Methods: random forest, ridge, SVM, MLP, GRU. Test: ten held-out years (2008-2017), training windows of varying length.
   - **Persistence result:** persistence was the better of two naive benchmarks. With 5 years of training, random forest was about 11% lower in RMSE and 16.4% lower in percent error than persistence. The neural net (MLP) never beat the benchmarks reliably. Ridge needed about 4 years to win; a GRU needed 8 to 20. A handful of top features did as well as all 13.
   - Why useful: gives a template (compare to persistence and seasonal naive, vary training length, drop features) and a warning about neural nets on small data. Sure: high.

2. **Gupta and Gupta 2025, "Time series forecasting of chlorophyll-a concentrations in the Chesapeake Bay."** Scientific Reports 15:30877. https://www.nature.com/articles/s41598-025-16352-3 [OPENED]
   - Place/target: three Chesapeake regions, **weekly** satellite chlorophyll 1997-2020, one week ahead. Method: LSTM (neural net) on the past 12 weeks of chlorophyll only. Test: last 15% of the record (about 2017-2020).
   - Compared with ARIMA and TBATS only. **I found no persistence baseline** in the text (searched for the word). RMSE 0.121 / 0.155 / 0.199 mg/m3.
   - Lesson: a pure past-values model, no weather, nothing about events. Treat its "win" as unproven against persistence.

3. **Yan and Alamdari 2024, "Predicting coastal harmful algal blooms using integrated data-driven analysis of environmental factors."** Sci. Total Environ. 912:169253. https://pubmed.ncbi.nlm.nih.gov/38101630/ [OPENED]
   - Place: Biscayne Bay, Florida (coastal). Target: monthly chlorophyll-a, one-month lead. Method: tree ensembles with SHAP importance. R2 0.92 for 1-month-ahead, 0.69 for same-month.
   - Top features included **current-month chlorophyll** (i.e. persistence information), land use, total phosphorus and nitrogen oxides. No persistence baseline reported in the abstract. The 1-month-ahead score being higher than same-month is odd and should make us suspicious of how the data was split (my opinion, UNVERIFIED).

4. **Shen and Chen 2026, Comment on Recknagel et al. (2025), Water Research.** https://www.sciencedirect.com/science/article/abs/pii/S0043135426000886 [SNIPPET; PubMed copy BLOCKED]
   - A critique of a 5-day cyanobacteria early-warning study in Lake Müggelsee, Germany. They say four choices may overstate skill: cross-year preprocessing and interpolating weekly data to hourly/daily (leakage); using R2/RMSE instead of event metrics; and weak baselines. They recommend leakage-robust validation, event-based metrics, uncertainty and strong baselines. Directly relevant to our redo.

5. **Zhang et al. 2025, "Enhancing short-term algal bloom forecasting through an anti-mimicking hybrid deep learning method."** J. Environ. Management. DOI 10.1016/j.jenvman.2025.124832 (PubMed id 40068506, BLOCKED). [INDEX, truncated abstract]
   - Says a common problem in time-series forecasting is "data replication", where models tend to copy the last value (that is, behave like persistence). They propose a method to avoid it. I did not see their results.

6. **Huang and Ushio 2026, "Exploring causal factors of coastal chlorophyll-a dynamics ... near future forecasting."** Marine Pollution Bulletin. DOI 10.1016/j.marpolbul.2026.120163 [INDEX, full abstract seen]
   - Hong Kong waters, empirical dynamic modeling. Salinity was the strongest causal factor in the in-situ data, but **adding the causal factors did not greatly improve forecasts**. For satellite data, adding sea surface temperature improved forecasts at most sites. Matches our finding that extra inputs often add little.

7. **Wang et al. 2026, 24-hour algal abundance forecasts in a reservoir (Toxins 18:203).** https://pmc.ncbi.nlm.nih.gov/ (PMC13211262, PMC page BLOCKED) [INDEX]
   - Freshwater reservoir, hourly data, Transformer net. R2 0.88 predicting the next hour. SHAP says **previous-hours algal abundance** was the main driver, followed by oxygen, air temperature, wind, pH. Again, persistence-like inputs dominate.

8. **Zhou et al. 2026, cross-dataset benchmark of ML for marine and atmospheric prediction.** PLOS ONE. DOI 10.1371/journal.pone.0351325 [INDEX, full abstract]
   - Leakage-aware benchmark across 7 datasets mostly Chinese coastal waters. Finds tree ensembles are strong baselines, LSTMs help only when time structure is central, quality-controlled chlorophyll is comparatively predictable, but event-driven biotoxins stay hard. "Skill depends more on target structure and covariate quality than model complexity."

9. **Sun et al. 2024, Fourier analysis plus Transformer for coastal chlorophyll-a forecasts.** Water Research. DOI 10.1016/j.watres.2024.122160 (PubMed id 39096816, BLOCKED). [INDEX, truncated abstract; results not seen]

10. **Jiang et al. 2026, ChlCast (arXiv 2611.17704).** https://arxiv.org/abs/2611.17704 [OPENED abstract only]
   - 10-day, 4 km global satellite chlorophyll forecast. Beats the operational Copernicus biogeochemical model: error cut about 47-71% against satellite fields and 13-35% against float observations. Compared against another model, not persistence. Open-ocean scale; not for turbid shallow estuaries.

11. **Page et al. 2018, "Adaptive forecasting of phytoplankton communities."** Water Research. DOI 10.1016/j.watres.2018.01.046 [INDEX, truncated]. Lake study; listed for completeness, not read.

12. **Park et al. 2015 (published online 2014), early-warning protocol for chlorophyll-a using ANN and SVM in Korean freshwater and estuarine reservoirs.** Sci. Total Environ. DOI 10.1016/j.scitotenv.2014.09.005 [INDEX, truncated]. Older; not read.

**What I did not find:** a paper forecasting "will daily-mean chlorophyll cross its station's 90th percentile in the next 1 to 3 days" at fixed estuary sensors, with persistence reported. That may exist behind searches I did not run. UNVERIFIED.

---

## 3. San Francisco Bay specifically

What the sources say drives blooms there, and whether we can measure it at a station.

- **Nardelli et al. 2026**, "Assessing environmental drivers and protist community dynamics that shaped the historic August 2022 Heterosigma akashiwo bloom in San Francisco Bay." Estuaries and Coasts. https://link.springer.com/article/10.1007/s12237-025-01629-7 [OPENED]
  - Chlorophyll topped 450 ug/L, normal summers sit under 10. Water in 2022 was unusually dry: about 10% saltier surface, 70% less stratified, 36% less river inflow than other years. A big June diatom bloom drew down nutrients; few dinoflagellate grazers in July; then suitable conditions (13 to 14 hours of daylight, 17 to 21 C, nitrate 17 to 24 umol/L, **neap tides**) let the bloom grow from 0.03% to 48% of protists between July 20 and August 25. The bloom collapsed as a grazing dinoflagellate rose and possibly as the tide shifted from neap to spring (more mixing). Long-run context: lower turbidity and decreasing wind speeds, fewer bottom clams grazing, shift in spring bloom timing.
  - Takeaway: it is a combination of physics (neaps, light, warmth, calm) and biology (grazers). Biology we can't see at a sensor; physics we can.
- **USGS summary of that study**: https://www.usgs.gov/centers/california-water-science-center/news/heterosigma-akashiwo-san-fracisco-bay [SNIPPET]. A similar, weaker bloom recurred in September 2023 per that page; the Water Board FAQ [SNIPPET] gives late July 2023 and says it faded by early August, so the dates in my sources disagree: UNVERIFIED which is right.
- **Cloern, Cole, Wong, Alpine 1985**, "Temporal dynamics of estuarine phytoplankton: a case study of San Francisco Bay." Hydrobiologia. https://www.usgs.gov/publications/temporal-dynamics-estuarine-phytoplankton-a-case-study-san-francisco-bay [OPENED]
  - South Bay: long residence time (months), growth high but balanced by clam grazing. Brief spring blooms (days to weeks) happen when the water column **stratifies**, freeing surface algae from grazers. The strength of stratification **varies over the neap-spring cycle**, so South Bay is highly dynamic over days. Wet years (more river discharge, more buoyancy) bring more persistent, intense spring blooms.
  - This is the single most on-point source for a 1 to 3 day horizon in South Bay.
- **Cloern and Jassby 2012**, Reviews of Geophysics, "Drivers of change in estuarine-coastal ecosystems: discoveries from four decades of study in San Francisco Bay." https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2012RG000397 [SNIPPET]. Snippet says neap-tide salinity stratification speeds surface growth and the bloom dissipates on the next spring tide; the Bay is more turbid than Chesapeake because wind waves and tides keep sediment suspended; light attenuation drives productivity.
- **Shallow-water studies**, e.g. Thompson et al. (ScienceDirect S0924796307002692). [SNIPPET] Net growth is positive only on the shallow shoals because the deep channel is too turbid; shoal blooms seed the channel; bloom size correlates with low tidal current speeds (near the spring equinox). Source of the "shoals vs channel" and "tidal energy" ideas.
- **SFEI / Water Board, 2023** staff report: https://www.waterboards.ca.gov/sanfranciscobay/board_info/agendas/2023/September/6_ssr.pdf [SNIPPET]. Says the 2022 trigger is not certain; possible contributors were many sunny days, low suspended sediment, possibly periods of little wind, and the alga's swimming behavior.
- **Salt ponds and sloughs:** I did not find a source I opened that quantifies exchange with salt ponds as a bloom driver. The SFEI conference abstract at https://www.sfestuary.org/wp-content/uploads/2013/10/32-Nutrients.pdf mentions chlorophyll on ebb tides 5-10x higher at a wetland-influenced station [SNIPPET]. UNVERIFIED as a general driver.
- **SFEI Moored Sensor Program** (the stations our model uses): 15 stations, 15-minute data, serviced every 3 to 6 weeks. https://www.sfei.org/programs/cw/nutrients/wq-monitoring [SNIPPET]; dataset page https://www.sfei.org/data/san-francisco-bay-high-frequency-water-quality-sensor-data-ver-1 returned HTTP 403 to my request [BLOCKED], but the search snippet lists measured parameters: temperature, salinity, depth, dissolved oxygen, chlorophyll, blue-green algae, turbidity, fluorescent dissolved organic matter and pH. Also a note that South Bay shoals show higher chlorophyll than the channel.
- **Satellite chlorophyll in SF Bay**: Kudela et al. 2024, Remote Sensing 16:1103, https://www.mdpi.com/2072-4292/16/6/1103 [SNIPPET]. Standard algorithms failed on the 2022 bloom; a refit red-edge algorithm worked across non-bloom (under about 30 mg/m3) and bloom (over 100) conditions. Sentinel-3 OLCI is about daily at 300 m; Sentinel-2 at 10 m returns only every 7 to 14 days.

**Drivers that could be measured from public data at station level (my read):**

| Driver | Source says | Station-level data |
|---|---|---|
| Neap/spring tide phase and tidal range | Stratification and surface growth on neaps; bloom ends on springs | Computable from the date alone (lunar phase) or from tide predictions at the nearest NOAA tide gauge; differs little between stations, but interacts with station depth |
| Stratification | Strong control (South Bay) | Salinity or temperature difference top vs bottom, only if a station has two depths; otherwise surface-only proxies are weak. UNVERIFIED which stations have two depths |
| Light / day length | 13 to 14 hours named in 2022 | Computable; same for every station |
| Turbidity | Light limitation; low sediment before 2022 bloom | Turbidity sensor at the station (differs by station) |
| Wind | Calm periods; wind resuspends sediment | Nearby weather station or model; one number for all stations unless a nearer gauge is used |
| Temperature | 17 to 21 C window | Sensor at the station |
| Residence time / river outflow | Seasonal and wet/dry-year effect | Delta outflow (old model already had it; added nothing) |
| Grazers, protist community | Strong control | Not at station level (needs cruise samples) |

---

## 4. Operational forecast systems worth copying or citing

- **C-HARM (California Harmful Algae Risk Mapping).** Anderson et al. 2016, Harmful Algae 59:1-18, https://sccoos.org/wp-content/uploads/2018/07/Anderson_HA_2016.pdf [OPENED, PDF text]; NOAA summary https://coastalscience.noaa.gov/data_reports/initial-skill-assessment-of-the-california-harmful-algae-risk-mapping-c-harm-system/ [SNIPPET]
  - Target: probability of toxic Pseudo-nitzschia / domoic acid on the open California coast (not SF Bay estuary). Inputs: ROMS ocean circulation model (3 km, 72-hour forecast), satellite chlorophyll (MODIS) filled in with a gap-filling method (DINEOF) and projected up to 3 days ahead, plus sea surface temperature and salinity. Daily maps on the CeNCOOS site; the project description says it was to be folded into NOAA's operational HAB forecast system.
  - Skill: I saw an accuracy of about 43% at one setting and a best balanced point of roughly 68% for hits with about 57% false-alarm ratio at one threshold, but I read only extracts and cannot be sure which model and station they belong to. UNVERIFIED numbers; do not cite them without re-reading. A "full model" (with in-situ data) beat a "remote-sensing only" model, but only the latter can run daily. No persistence comparison seen.
  - Copyable ideas: gap-filling for clouds, a 3-day horizon, reporting hits, misses and false alarms (not just R2).
- **NOAA Lake Erie HAB forecast.** https://coastalscience.noaa.gov/science-areas/habs/hab-forecasts/lake-erie/ [SNIPPET] and https://www.noaa.gov/news-release/moderate-to-above-moderate-harmful-algal-bloom-predicted-for-western-lake-erie [SNIPPET]. Combines satellite imagery (bloom location and extent), a forecast and vertical-mixing model, and field toxicity samples; gives current extent and a 5-day outlook of where the bloom will move. The 5-day outlook moves an observed bloom around with currents and wind (transport), which is different from predicting a new bloom. The experimental predecessor archive notes clouds blocked satellite data on some days and they reused the latest cloud-free image: https://www.glerl.noaa.gov/res/HABs_and_Hypoxia/habTracker.html [SNIPPET]. Skill numbers: not found.
- **NOAA Gulf of Mexico (Karenia brevis) HAB-OFS.** https://oceanwatch.noaa.gov/cwn/news/2019-02-15/harmful-algal-bloom-monitoring-and-forecasting-gulf-america.html [SNIPPET]. Uses satellite ocean color, cell counts and environmental info; bulletins give a 3 to 4 day forecast of respiratory-irritation risk. A skill assessment exists (https://pmc.ncbi.nlm.nih.gov/articles/PMC2902173, BLOCKED); not read, so no numbers.
- **Gulf of Maine Alexandrium:** mentioned only as an example in NOAA text (works partly because the alga forms cysts that can be counted). No forecast details opened. UNVERIFIED.
- **CyAN** (EPA/NASA/NOAA/USGS cyanobacteria network): not opened.

---

## 5. Honest lessons from this literature

1. **Leakage.** Interpolating sparse samples to daily or hourly, preprocessing across years, and random splits let tomorrow's information into training. See Shen and Chen 2026 (item 2.4, [SNIPPET]) and the leakage-aware framing in Zhou 2026 [INDEX]. A 2026 MDPI review also says interpolation, temporal leakage and split strategy can affect performance: https://www.mdpi.com/2076-3417/16/15/7469 [SNIPPET].
2. **Persistence hides inside the inputs.** Wang 2026 and Yan 2024 both find last-known chlorophyll or algae is the top feature; Zhang 2025 names "data replication" as a standard failure. Beckmann 2025 is the model of doing it right (persistence plus seasonal naive, many test years).
3. **Judge on events, not R2.** R2/RMSE reward getting the quiet days right. Use precision-recall, hits, misses, false-alarm ratio. (C-HARM does; the Müggelsee critique asks for it.)
4. **Small event counts.** Beckmann 2025 needed about 4 or more years to beat persistence reliably; we have [redacted: from the restricted Bay file]. Use rolling test years and report intervals.
5. **Satellite chlorophyll in turbid shallow water** is unreliable with standard blue-green algorithms because sediment and dissolved organic matter confuse the signal (several papers, e.g. https://www.mdpi.com/2077-1312/14/4/360 [SNIPPET], https://www.sciencedirect.com/science/article/abs/pii/S0273117718301662 [SNIPPET]). In SF Bay in 2022, standard algorithms failed on the bloom (Kudela 2024 [SNIPPET]). A locally refit red-edge algorithm is the fix.
6. **Clouds and fog.** The Tick Tick Bloom problem page says imagery within about 10 days is only "generally" representative, and L2 atmospheric correction can hide bright blooms [OPENED]. C-HARM gap-fills clouds with a statistical method [OPENED]. I did not find a source quantifying fog effects in SF Bay. UNVERIFIED.
7. **Weather features often add little.** Tick Tick Bloom winners found precipitation and wind unhelpful [OPENED]; Hong Kong EDM found causal inputs did not greatly improve forecasts [INDEX]. This supports the old Model 3 result.

---

## Ideas ranked by expected value for our 1-to-3-day station warning

Ranking is my judgment (Claude), not tested. "Data" lists what each needs.

1. **Always report the one-input persistence rule and a seasonal-naive rule next to every model, across rolling test years, with event metrics.** Physical reason: none needed; it is how we know whether anything works. Data: what we already have. Evidence: Beckmann 2025 [OPENED], Shen and Chen 2026 [SNIPPET].
2. **Neap-spring tide phase (and a 1 to 3 day lead of it) as a station-by-depth feature.** Reason: neap tides weaken mixing so South Bay can stratify, letting surface algae grow free of bottom grazers; spring tides end blooms (Cloern 1985 [OPENED], Nardelli 2026 [OPENED]). Data: tide predictions from the date; interacts with each station's depth, so it can separate stations. Risk: the old model already had a 7-day tide cycle and tide range and got nothing, but those were one number copied to all nine stations. Try it interacted with station depth/type (shoal vs channel).
3. **Neighboring stations' chlorophyll (upstream and downstream, lagged).** Reason: blooms move with currents and shoals seed channels (Thompson et al. [SNIPPET]; Lake Erie transport forecasts [SNIPPET]). Differs station to station on the same day, unlike the old inputs. Data: the existing sensor network.
4. **Station-level turbidity, temperature and their recent changes (1 to 3 day trend).** Reason: light and warmth windows (17 to 21 C, low sediment before 2022 bloom: Nardelli [OPENED], Water Board [SNIPPET]). Data: same sensors; already partly in old model, so test as changes and not levels.
5. **Daily satellite chlorophyll (Sentinel-3 OLCI, about daily at 300 m) near each station, if it can be gap-filled.** Reason: differs by station each day and arrives in time; Kudela 2024 shows a refit algorithm for SF Bay exists [SNIPPET]. Risks: clouds and fog, turbid shallows, 300 m pixels near shoals, and whether sensors' own chlorophyll already carries the same information. Data: Sentinel-3 OLCI public archive plus the SF Bay algorithm; heavy work, uncertain payoff.
6. **Wind with a local gauge (calm spells and speed 1 to 3 days back), as a short-window feature.** Reason: calm periods named for 2022 and wind drives resuspension and mixing (Nardelli [OPENED], Water Board [SNIPPET]). Data: nearest weather station per station, not a Bay-wide number. Expected gain low (winners and Hong Kong study found wind weak).
7. **Region-specific models and tree-boosting ensembles with simple summary features**, per the Tick Tick Bloom winners [OPENED]; must be reported next to the simple rule per the house rule in the old facts file.
8. **Delta outflow.** Reason: seasonal and wet-year effect on South Bay stratification (Cloern 1985 [OPENED]). The old test showed a change of [redacted: from the restricted Bay file] at daily scale, so only worth keeping as a slow, seasonal context feature. Lowest priority.
9. **Not at station level, skip for now:** grazer and protist community, nutrient pulses, salt-pond exchange (no quantified source found).

## What I would do next (suggestions only, nothing acted on)
- Open the three Tick Tick Bloom write-up reports in the repo (1st, 2nd, 3rd place folders) to see the exact features and validation.
- Open the Kudela 2024 paper in full and Cloern 2012 in full; both were only snippets for me.
- Search specifically for "event-based" or "exceedance" chlorophyll forecasts at sensor buoys (Chesapeake, Gulf, Baltic, Korean and Japanese estuaries); my search was broad, not exhaustive.
- Ask SFEI (via the existing outreach draft) which stations have two-depth sensors, since stratification is the best-supported driver.
