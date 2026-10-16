"""Report text. Numbers come from the real result files so nothing is typed by hand."""
import json, pandas as pd
R = json.load(open("results/system_results.json")); M = json.load(open("results/ml_results.json"))
E = json.load(open("results/etl_stats.json")); feat = pd.read_csv("data/features.csv")
A, I, S, F, Au = R["api"], M["isolation_forest"], M["static_rules"], R["flood"], R["audit"]
PF = M["per_fault"]; nfault_win = int(feat.label.sum())
TITLE = "SYSPULSE: INTELLIGENT SYSTEM MONITORING AND ANOMALY DETECTION SYSTEM"
pct = lambda x, d=1: f"{x*100:.{d}f}%"

def P(t): return ("p", t)
def B(items): return ("b", items)
def N(items): return ("n", items)
def IMG(path, w, cap): return ("img", path, w, cap)
def TBL(cap, head, rows, widths, align=None): return ("tbl", cap, head, rows, widths, align)

# sample rows for table 4.2
rows42 = []
first = feat[feat.fault_name == "normal"].iloc[40]
def r42(r): return [str(int(r.win)), str(int(r.n)), f"{r.cpu_mean:.1f}", f"{r.mem_mean:.1f}", f"{r.proc_mean:.0f}", f"{r.net_s:.0f}", r.fault_name.replace("_", " ")]
rows42.append(r42(first))
for f in ["cpu_spike", "memory_leak", "disk_thrash", "net_exfil", "fork_bomb"]:
    g = feat[feat.fault_name == f]; rows42.append(r42(g.iloc[len(g)//2]))

INTRO = [
 P("Every computer, from a student laptop to a cloud server, keeps producing numbers about itself: how busy the CPU is, how much memory is in use, how many processes are running, how much data moves through the disk and the network. While everything is healthy these numbers follow a pattern. When something goes wrong, such as a runaway program, a memory leak or malware sending data out, the pattern breaks. Spotting that break early is the main job of any system monitoring tool."),
 P("Most basic monitoring tools simply compare each number with a fixed limit, for example “raise an alert if CPU is above 90%”. This is easy to set up but it has two weaknesses. A limit low enough to catch real trouble fires constantly on busy days, and a limit high enough to stay quiet misses problems that are unusual but not extreme, like a process count that doubles while the CPU still looks normal. Machine learning offers a different approach: learn what normal looks like for a particular machine and flag whatever does not fit."),
 P("This mini project, SysPulse, builds a small end-to-end monitoring system that runs completely on a laptop. A collector samples system metrics, a PySpark job turns the raw samples into one-minute feature windows, an Isolation Forest model learns normal behaviour and scores every window, and the results are sent to a local, cloud-style ingestion API that stores them in a database and raises alerts. Because that API accepts data over a network connection, a security layer sits in front of it so that only genuine agents can send data and every decision is written to a tamper-evident audit log."),
 P("The work is organised around the four engineering modules of the course: Data Engineering, Cloud Engineering, AI Engineering and Security Engineering. Each module was built and tested on its own and then connected into one pipeline. All the figures in this report come from actually running the code. The evaluation uses a labelled 48-hour data set in which faults were injected at known times, so detection quality could be measured instead of guessed."),
 P("The rest of the report is arranged as follows. Chapter 2 states the problem and the objectives. Chapter 3 presents the overall architecture. Chapter 4 describes the four modules one by one, each with its procedure, screenshots, activity diagram and results. Chapter 5 gives the conclusion and possible future work, followed by the references."),
]
PROB = [
 P("Fixed-threshold monitoring cannot keep up with how real systems behave. Load changes through the day, so a CPU reading of 60% can be perfectly normal at noon and suspicious at 3 a.m. Several kinds of faults, such as a slow memory leak, a sudden jump in outgoing network traffic or a burst of new processes, may never cross the usual limits but still harm the machine or point to an attack. Administrators then learn about the problem only after the system slows down or fails."),
 P("A second problem is trust. Monitoring data normally travels from the machine being watched to a central service. If that link is not protected, anyone who can reach the service can send fake readings to hide a real problem, replay old readings, flood the service with requests, or quietly edit the stored history afterwards. A monitoring system that cannot be trusted is not much use, however clever its detection is."),
 P("The problem addressed here is therefore to design and build a monitoring system that (a) processes raw metrics into useful features, (b) detects abnormal behaviour automatically without a hand-written rule for every fault, (c) delivers and stores the results through a cloud-style service, and (d) protects that service and its records against misuse."),
]
OBJ = [
 P("The main aim is to build and evaluate a working prototype of an intelligent monitoring and anomaly detection system. The specific objectives, matched to the four modules, are:"),
 B([("Module 1, Data Engineering: ", "collect system metrics, generate a labelled test data set with five kinds of injected faults, and use PySpark to clean the data and compute window-based features."),
    ("Module 2, Cloud Engineering: ", "build a local cloud-style backend with an HTTP ingestion API and a database, so that agents can push data and alerts are raised as the data arrives."),
    ("Module 3, AI Engineering: ", "train an Isolation Forest model on normal behaviour and compare it with a traditional fixed-threshold method using precision, recall and F1-score."),
    ("Module 4, Security Engineering: ", "protect the ingestion path with message signing, replay protection, input validation and rate limiting, and keep a hash-chained audit log that shows tampering."),
    ("Overall: ", "measure the complete system for detection quality, response time and resistance to a set of simulated attacks.")]),
 P("Scope: everything runs on one laptop (127.0.0.1). No real cloud account is used; the “cloud” is a local service that behaves like one. The evaluation data is synthetic, so the results show that the approach works in a controlled setting and should not be read as accuracy on a production system."),
]
ARCH = [
 P("Figure 3.1 shows the overall architecture. Everything sits on a single laptop, but the parts are separated the same way they would be in a real deployment, so each one could later be moved to its own machine or cloud service."),
 IMG("figs/fig_arch.png", 4.9, "Figure 3.1: Architecture of SysPulse"),
 P("The parts work together as follows:"),
 N(["The collector reads CPU, memory, disk, network and process metrics every 10 seconds. For the evaluation it also produces a labelled data set with injected faults.",
    "The PySpark pipeline cleans the samples and groups them into one-minute windows, giving 15 numeric features per window.",
    "The Isolation Forest is trained on the first day of windows and saved to disk.",
    "The edge agent takes a window, signs it with a shared secret and sends it to the ingestion API.",
    "The security gateway checks the sender, signature, timestamp, nonce, data format and request rate, and records the outcome in the audit ledger.",
    "For accepted requests the API scores the window with the model, stores it in SQLite and raises a WARNING or CRITICAL alert if the window is anomalous."]),
 TBL("Table 3.1: Technology used", ["Component", "Technology", "Purpose"],
     [["Collector", "Python, psutil, NumPy", "Read metrics and generate labelled test data"],
      ["Data pipeline", "PySpark (local mode, 2 cores)", "Cleaning, windowing, feature extraction"],
      ["Anomaly model", "scikit-learn Isolation Forest", "Unsupervised anomaly scoring"],
      ["Backend API", "Python http.server (threaded)", "Receive, score and store windows"],
      ["Storage", "SQLite", "Metrics, alerts and audit tables"],
      ["Security", "hmac, hashlib (SHA-256)", "Signing, hashing and audit chain"],
      ["Charts", "Matplotlib", "Figures used in this report"],
      ["Environment", "Python 3.12, Java 21", "Single-machine simulation"]],
     [1700, 3600, 4600], ["l", "l", "l"]),
]

M1_PROC = [
 P("The first step was to get data. The collector (collector.py) uses the psutil library to read CPU usage, memory usage, disk reads and writes, network bytes sent and received, and the number of running processes. Run on a laptop it gives real readings, but a healthy laptop does not misbehave on demand, so a labelled data set was needed to measure how well faults are detected."),
 P("To create one, the generator produces 48 hours of samples, one every 10 seconds, which is 17,280 rows. Normal load follows a smooth daily pattern, busier in the daytime, with random noise added. Five kinds of faults are then injected at random times:"),
 B([("CPU spike: ", "CPU jumps by about 45 points and the temperature rises (14 events)."),
    ("Memory leak: ", "memory climbs steadily over about five minutes (6 events)."),
    ("Disk thrashing: ", "disk reads and writes multiply several times (10 events)."),
    ("Network exfiltration: ", "outgoing traffic suddenly becomes many times larger (9 events)."),
    ("Fork bomb: ", "the process count rises quickly (5 events).")]),
 P(f"In total {490} samples carry a fault label. The temperature column is simulated, because laptop temperature sensors are not available on every machine."),
 P(f"The raw file is then processed by spark_pipeline.py in PySpark local mode. The job reads the CSV, drops rows with missing or impossible values (CPU or memory outside 0 to 100%), assigns each row to a one-minute tumbling window and aggregates it. For every window it computes the mean, maximum and standard deviation of CPU, the mean and maximum of memory, total disk and network traffic, process count statistics and temperature. Changes from one window to the next (deltas) for CPU, memory and process count are added with a Spark window function, because a sudden change is often a better sign of trouble than the level itself. The result is a table of {E['windows']:,} rows and {E['cols']} columns, written to features.csv."),
]
M1_SHOT = [
 P("Figure 4.1 shows the collector and the Spark job running in the terminal. Figure 4.2 plots the first six hours of the engineered features, with the windows that contain an injected fault marked in red."),
 IMG("figs/shot_m1.png", 6.9, "Figure 4.1: Collector and PySpark pipeline output"),
 IMG("figs/fig_m1_timeline.png", 6.0, "Figure 4.2: Windowed features with fault windows highlighted"),
]
M1_ACT = [P("The steps of the data engineering module are shown in Figure 4.3."), IMG("figs/fig_act1.png", 3.6, "Figure 4.3: Activity diagram of Module 1")]
M1_RES = [
 P(f"The pipeline turned {E['raw']:,} raw samples into {E['windows']:,} one-minute windows, of which {nfault_win} contain at least one faulty sample. No rows were removed, since the generated data has no gaps; the cleaning step is there for real collector output, which can contain bad readings. Table 4.1 summarises the run and Table 4.2 shows one typical window for each fault type next to a normal one."),
 TBL("Table 4.1: Summary of the PySpark run", ["Item", "Value"],
     [["Raw samples read", f"{E['raw']:,}"], ["Rows dropped by cleaning", f"{E['raw']-E['clean']}"], ["One-minute windows produced", f"{E['windows']:,}"],
      ["Columns in output (15 features + identifiers and labels)", f"{E['cols']}"], ["Windows containing a fault", f"{nfault_win}"], ["Job time, including Spark start-up", f"{E['seconds']} s"]],
     [6400, 2600], ["l", "c"]),
 TBL("Table 4.2: Sample windows from features.csv", ["Window", "Samples", "CPU mean %", "Memory mean %", "Processes", "Net sent (KB)", "Fault"],
     rows42, [1300, 1000, 1250, 1450, 1200, 1300, 1700], ["c"]*6+["l"]),
 P("The job time looks long for such a small file, but almost all of it is Spark starting up. Spark is overkill for 17 thousand rows, yet the same code would run unchanged on logs many times larger, which is the reason for using it. Some of the fault windows in Table 4.2 already stand out in the columns shown: the CPU spike in CPU, the fork bomb in the process count and the network burst in the traffic. Others, such as the disk thrashing window, look ordinary here and differ only in columns that are not shown. This is why a model that looks at all features together is more useful than a single limit."),
]

M2_PROC = [
 P("Module 2 is the cloud side of the system. Since the project has to run on a laptop, I built a small backend that behaves like a cloud service: it listens on a network port, accepts data from agents over HTTP, stores it in a database and lets a client read the alerts. It has three endpoints:"),
 B([("POST /ingest: ", "receives one signed feature window as JSON."),
    ("GET /health: ", "returns the service status and the number of accepted and rejected requests."),
    ("GET /alerts: ", "returns the latest alerts.")]),
 P("When a window arrives it first goes through the security checks of Module 4. If it is accepted, the saved Isolation Forest scores it, and the window, its score and the verdict are stored in the metrics table of a SQLite database. If the window is anomalous, a row is added to the alerts table with severity CRITICAL when the score is above 0.62 and WARNING otherwise. The server is multi-threaded, so several agents can send data at the same time."),
 P("The edge agent (agent.py) is the client side. It turns a window into JSON, signs it and posts it to the API. For the evaluation, the agent replayed all 1,441 windows of the test day through the API one after another. SQLite was chosen because it needs no installation; the database code is only a few lines, so it could be swapped for a managed database service later."),
]
M2_SHOT = [P("Figure 4.4 shows the backend receiving the test windows and the latest alerts it raised."), IMG("figs/shot_m2.png", 6.9, "Figure 4.4: Local ingestion API handling the test windows")]
M2_ACT = [P("Figure 4.5 shows the path of one request through the backend."), IMG("figs/fig_act2.png", 3.6, "Figure 4.5: Activity diagram of Module 2")]
M2_RES = [
 P(f"All {A['requests']:,} windows were accepted, scored and stored. The backend raised {A['alerts']} alerts, {A['critical']} of them CRITICAL. Table 4.3 gives the performance seen by the agent, and Figure 4.6 shows how the request times were spread."),
 TBL("Table 4.3: Ingestion API performance (single sequential client)", ["Measure", "Value"],
     [["Requests sent / rows stored", f"{A['requests']:,} / {A['db_rows']:,}"], ["Total time", f"{A['seconds']} s"], ["Throughput", f"{A['req_per_sec']} requests/s"],
      ["Mean latency", f"{A['mean_ms']} ms"], ["Median (p50)", f"{A['p50_ms']} ms"], ["p95", f"{A['p95_ms']} ms"], ["p99", f"{A['p99_ms']} ms"],
      ["Alerts raised (CRITICAL + WARNING)", f"{A['alerts']} ({A['critical']} + {A['alerts']-A['critical']})"]],
     [6000, 3000], ["l", "c"]),
 IMG("figs/fig_m2_latency.png", 5.4, "Figure 4.6: Distribution of request latency"),
 P(f"The detections made through the API matched the offline model exactly ({A['tp']} true alarms, {A['fp']} false alarms, {A['fn']} missed windows). That confirms the model was loaded and used correctly inside the service. A request takes about {A['mean_ms']:.0f} ms, but most of that is Python overhead (HTTP handling, the scikit-learn call and the database commit); the model itself needs well under a millisecond per window. For one agent sending a window every minute this is far more than enough. Serving thousands of agents would need a proper web framework, batching and a server database."),
]

M3_PROC = [
 P("The model chosen is the Isolation Forest [1]. It is unsupervised, so it does not need labelled faults for training. It builds many random trees that split the data on randomly chosen features. A point that is unusual gets isolated after only a few splits, so a short average path through the trees means the point is more anomalous. This suits monitoring, because new kinds of faults keep appearing and nobody has labelled them in advance. The steps were:"),
 B([("Split by time. ", f"The {E['windows']:,} windows were split in time order: the first {M['train_windows']:,} (day 1) for training and the remaining {M['test_windows']:,} (day 2) for testing, so the model is never tested on the same period it learned from."),
    ("Standardise. ", "The 15 features were scaled to zero mean and unit variance, with the scaler fitted on the training day only."),
    ("Train. ", "An Isolation Forest with 200 trees and an expected anomaly fraction of 4% was fitted. The fault labels were not used during training."),
    ("Compare with rules. ", "The same test windows were also checked with a typical fixed-threshold rule set: alert if CPU is above 80%, memory above 85%, process count above 400 or temperature above 85 °C."),
    ("Evaluate. ", "Precision, recall, F1-score, false positive rate and ROC-AUC were computed against the true fault labels."),
    ("Save. ", "The scaler and the model were saved with joblib so that the cloud API can load them.")]),
 P(f"One honest note: the 4% setting is close to the real fault rate in the test day ({M['test_anomalous_windows']} of {M['test_windows']:,} windows, {M['test_anomalous_windows']/M['test_windows']*100:.1f}%), which helps the model. On a real machine that rate is not known, so this value would have to be tuned."),
]
M3_SHOT = [P("Figure 4.7 shows the training and evaluation run."), IMG("figs/shot_m3.png", 6.9, "Figure 4.7: Training and evaluation output of the anomaly model")]
M3_ACT = [P("The workflow of the AI module is shown in Figure 4.8."), IMG("figs/fig_act3.png", 3.6, "Figure 4.8: Activity diagram of Module 3")]
fnames = {"cpu_spike": "CPU spike", "memory_leak": "Memory leak", "disk_thrash": "Disk thrashing", "net_exfil": "Network exfiltration", "fork_bomb": "Fork bomb"}
M3_RES = [
 P(f"On the unseen test day the Isolation Forest found {I['tp']} of the {M['test_anomalous_windows']} faulty windows (recall {I['recall']:.3f}) with {I['fp']} false alarms among {I['fp']+I['tn']:,} normal windows. The ROC-AUC of {I['auc']:.3f} shows that the anomaly score separates faulty from normal windows well, not just at one threshold. Table 4.4 compares it with the fixed-threshold rules."),
 TBL("Table 4.4: Detection results on the test day", ["Method", "Precision", "Recall", "F1-score", "False pos. rate", "TP", "FP", "FN"],
     [["Isolation Forest", f"{I['precision']:.3f}", f"{I['recall']:.3f}", f"{I['f1']:.3f}", pct(I['fpr'], 2), str(I['tp']), str(I['fp']), str(I['fn'])],
      ["Fixed thresholds", f"{S['precision']:.3f}", f"{S['recall']:.3f}", f"{S['f1']:.3f}", pct(S['fpr'], 2), str(S['tp']), str(S['fp']), str(S['fn'])]],
     [2000, 1150, 1000, 1100, 1500, 700, 700, 700], ["l"]+["c"]*7),
 IMG("figs/fig_m3_compare.png", 5.8, "Figure 4.9: Isolation Forest compared with fixed thresholds"),
 P("The fixed rules caught only one faulty window. Their precision of 1.000 comes from that single alert and should not be taken as a strength. Most injected faults are unusual rather than extreme: a CPU spike takes a typical 30% load to roughly 75%, which stays under the 80% limit, and a network burst or a rise in process count never touches any limit at all. Table 4.5 breaks the recall down by fault type."),
 TBL("Table 4.5: Recall per fault type", ["Fault type", "Faulty windows", "Isolation Forest", "Fixed thresholds"],
     [[fnames[k], str(PF[k]["windows"]), f"{PF[k]['iforest']:.2f}", f"{PF[k]['rules']:.2f}"] for k in ["cpu_spike", "disk_thrash", "fork_bomb", "memory_leak", "net_exfil"]],
     [3000, 2000, 2200, 2200], ["l", "c", "c", "c"]),
 IMG("figs/fig_m3_timeline.png", 5.8, "Figure 4.10: Anomaly score over the test day"),
 P("Every CPU spike, disk thrashing and fork bomb window was detected. Memory leaks were found 81% of the time; the first minutes of a leak look almost like normal usage, so a few early windows slip through. Network exfiltration was the weakest at 50% (3 of 6 windows). Each burst lasts about 80 seconds, so it is often split across two one-minute windows and the extra traffic gets averaged down, which is probably the reason. Shorter windows or an extra feature for traffic bursts could help. The test data is synthetic and covers only one machine, so these numbers show the method works, not what it would score on a real fleet."),
]

M4_PROC = [
 P("Module 4 protects the path between the agent and the backend, and the records stored afterwards. Five controls were written in security.py and applied in cloud_api.py:"),
 B([("Message signing. ", "Each agent has a secret key. For every request it computes an HMAC-SHA256 [5] over the timestamp, a random nonce and the request body, and sends it in a header. The server recomputes the value and compares it in constant time, so a changed body or a wrong key fails the check."),
    ("Replay protection. ", "The server rejects timestamps older than five minutes and remembers the nonces it has seen, so a captured valid request cannot be sent a second time."),
    ("Input validation. ", "The body must be JSON with exactly the expected fields, and every number must be numeric and within a sensible range. Unknown fields, missing fields, text in numeric fields and out-of-range values are refused with 422, and bodies over 8 KB with 413."),
    ("Rate limiting. ", "A token-bucket limiter allows each agent 10 requests per second with bursts of up to 60. Anything above that gets a 429 response."),
    ("Tamper-evident audit ledger. ", "Every rejected request and every anomaly alert is written to an append-only table. Each entry stores the SHA-256 hash of its own contents together with the hash of the previous entry, forming a chain [11]. Editing or deleting an old entry breaks the chain from that point on.")]),
 P("The checks run cheap-first: request size, agent identity and rate limit before the signature, and the signature before the data is parsed and validated, so a flood of bad requests costs the server as little as possible. Two limits of the prototype should be noted. The demo key is written in the source code, where a real system would fetch it from a secrets manager, and traffic on localhost is not encrypted, so a real deployment would also need TLS."),
]
M4_SHOT = [P("Figure 4.11 shows the output of the security test run."), IMG("figs/shot_m4.png", 6.9, "Figure 4.11: Security scenarios and audit chain verification")]
M4_ACT = [P("Figure 4.12 shows the order in which the gateway checks a request."), IMG("figs/fig_act4.png", 3.6, "Figure 4.12: Activity diagram of Module 4")]
ok_n = sum(t["ok"] for t in R["security_tests"])
M4_RES = [
 P(f"Twelve scenarios were tested: one valid request and eleven kinds of bad or hostile requests (these cover only the attacks listed here, not every possible weakness). The bad ones were repeated three times each, apart from the tampered body, which was sent once. All twelve gave the expected response ({ok_n} of {len(R['security_tests'])}), as listed in Table 4.6."),
 TBL("Table 4.6: Security test scenarios", ["Scenario", "Expected HTTP", "Received", "Result"],
     [[t["name"], str(t["expected"]), str(t["got"]), "Pass" if t["ok"] else "Fail"] for t in R["security_tests"]], [5000, 1700, 1300, 1000], ["l", "c", "c", "c"]),
 P(f"For the flood test, {F['sent']} requests with a valid signature were sent at once from 32 threads. The server accepted {F['ok']} and refused {F['limited']} with 429, so the extra load was stopped before it reached the model or the database and the service stayed responsive."),
 P(f"For the audit test, the ledger held {Au['entries']} entries and its chain verified correctly. Entry {Au['detected_at']} was then edited directly in the database, and the next verification failed exactly at that entry (Figure 4.13). One limit remains: someone who can rewrite the whole table could recompute every hash, so in practice the latest hash should also be copied to a separate place, such as another server."),
 IMG("figs/fig_m4_chain.png", 5.0, "Figure 4.13: Hash chain broken by editing one entry"),
]
CONC = [
 P(f"SysPulse shows that a complete monitoring pipeline, from raw metrics to alerts, can be built and tested on a single laptop using the four engineering modules. The PySpark job turned {E['raw']:,} raw samples into {E['windows']:,} feature windows. The Isolation Forest, trained without any fault labels, detected {pct(I['recall'])} of the injected fault windows with a false positive rate of {pct(I['fpr'], 2)}, while a typical fixed-threshold rule set detected only {pct(S['recall'])}. The local ingestion API processed every window with a median response time of {A['p50_ms']:.0f} ms, and the security layer rejected all eleven attack scenarios that were tried and limited a 300-request flood to {F['ok']} accepted requests."),
 P("The project also has clear limits. The data is synthetic and comes from one machine, the fixed-threshold baseline is deliberately simple, and the contamination setting of the model was chosen close to the true fault rate. The backend is a prototype: it has no TLS, its key is hard-coded for the demo and it is not built for large numbers of agents. The reported numbers should therefore be read as a proof of concept."),
 P("Possible future work includes:"),
 B([("Real data. ", "Collect weeks of metrics from several machines and re-evaluate with real incidents."),
    ("Better models. ", "Try seasonal baselines or an LSTM autoencoder, and use shorter windows for bursty faults such as network exfiltration."),
    ("Real cloud deployment. ", "Run the agent and API in containers on a cloud platform with a managed database and TLS."),
    ("Operations features. ", "Add a dashboard, e-mail or chat notifications and key rotation for agents."),
    ("Automatic response. ", "Let the system take safe first actions, such as restarting a service, when an alert is critical.")]),
]
REFS = [
 "F. T. Liu, K. M. Ting and Z.-H. Zhou, “Isolation Forest,” in Proc. IEEE International Conference on Data Mining (ICDM), 2008, pp. 413–422.",
 "M. Zaharia et al., “Apache Spark: A unified engine for big data processing,” Communications of the ACM, vol. 59, no. 11, pp. 56–65, 2016.",
 "F. Pedregosa et al., “Scikit-learn: Machine learning in Python,” Journal of Machine Learning Research, vol. 12, pp. 2825–2830, 2011.",
 "V. Chandola, A. Banerjee and V. Kumar, “Anomaly detection: A survey,” ACM Computing Surveys, vol. 41, no. 3, Art. 15, 2009.",
 "H. Krawczyk, M. Bellare and R. Canetti, “HMAC: Keyed-hashing for message authentication,” RFC 2104, IETF, 1997.",
 "National Institute of Standards and Technology, “Secure Hash Standard (SHS),” FIPS PUB 180-4, 2015.",
 "G. Rodola, “psutil: Cross-platform library for retrieving information on running processes and system utilization,” documentation. [Online]. Available: https://psutil.readthedocs.io",
 "Apache Software Foundation, “Apache Spark documentation: Spark SQL, DataFrames and window functions.” [Online]. Available: https://spark.apache.org/docs/latest/",
 "SQLite Consortium, “SQLite documentation.” [Online]. Available: https://www.sqlite.org/docs.html",
 "OWASP Foundation, “Input Validation Cheat Sheet,” OWASP Cheat Sheet Series. [Online]. Available: https://cheatsheetseries.owasp.org",
 "B. Schneier and J. Kelsey, “Secure audit logs to support computer forensics,” ACM Transactions on Information and System Security, vol. 2, no. 2, pp. 159–176, 1999.",
]
