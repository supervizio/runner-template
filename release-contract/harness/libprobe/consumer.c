/*
 * The libprobe release consumer (brief section 4.1; release-contract/README.md,
 * section 5).
 *
 * `cargo test` proves the Rust sources. It does not prove what a release
 * publishes: a `libprobe.a` and a `probe.h`, which a C (or cgo) consumer
 * compiles against and links, on a machine that never saw the sources. This
 * program is that consumer and nothing more. It includes ONLY the published
 * `probe.h`, links ONLY the published `libprobe.a`, and asks the archive the
 * questions a consumer depends on:
 *
 *   version     probe_get_version() equals the release tag without its "v".
 *               CARGO_PKG_VERSION is frozen into the archive at compile time;
 *               seven libprobe releases once shipped an archive answering
 *               "0.2.0" under tags v0.2.1..v0.6.0.
 *   layout      probe_get_abi_fingerprint() is not the failure value 0, and for
 *               every carrier below, sizeof() from THIS header on THIS target
 *               equals the size the archive reports. A difference means header
 *               and archive describe different memory.
 *   runtime     probe_init, a handful of collectors whose answer every platform
 *               owes (cpu, memory, the smoke JSON envelope), probe_free_string
 *               and probe_shutdown, executed for real.
 *
 * It never includes a private header, never recompiles libprobe, and its only
 * input is the published pair, so it can live in this public repository.
 *
 * Usage: consumer <expected-version> <report.json>
 *   expected-version  bare semver, e.g. 0.7.0
 * Writes a JSON report and exits 0 iff every check passed, 1 if one failed,
 * 2 on bad usage or when the report cannot be written.
 */

#include "probe.h"

#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_CHECKS 64

typedef struct {
    const char *name;
    int ok;
    char detail[256];
} Check;

static Check checks[MAX_CHECKS];
static int n_checks;

static void record(const char *name, int ok, const char *fmt, ...)
    __attribute__((format(printf, 3, 4)));

static void record(const char *name, int ok, const char *fmt, ...) {
    if (n_checks >= MAX_CHECKS) {
        return;
    }
    Check *c = &checks[n_checks++];
    va_list ap;
    c->name = name;
    c->ok = ok;
    va_start(ap, fmt);
    vsnprintf(c->detail, sizeof c->detail, fmt, ap);
    va_end(ap);
    printf("%s %-28s %s\n", ok ? "PASS" : "FAIL", name, c->detail);
}

/* JSON string body: the archive's answers are text we did not write. */
static void json_str(FILE *f, const char *s) {
    fputc('"', f);
    for (; s && *s; s++) {
        unsigned char ch = (unsigned char)*s;
        if (ch == '"' || ch == '\\') {
            fprintf(f, "\\%c", ch);
        } else if (ch < 0x20 || ch >= 0x7f) {
            fprintf(f, "\\u%04x", ch);
        } else {
            fputc(ch, f);
        }
    }
    fputc('"', f);
}

static const char *result_text(ProbeResult r) {
    return r.error_message ? r.error_message : "(no message)";
}

/*
 * One sizeof per carrier, each spelled exactly as its typedef in probe.h. The
 * list is the carriers this consumer itself reads, plus the ones every
 * consumer's first calls pass by pointer; the README's rule for a consumer is
 * "check the carriers you actually read".
 */
#define CARRIER(T) {#T, sizeof(T)}
static const struct {
    const char *name;
    uint64_t size;
} carriers[] = {
    CARRIER(ProbeResult),
    CARRIER(ProbeCollectOptions),
    CARRIER(SystemCPU),
    CARRIER(SystemMemory),
    CARRIER(LoadAverage),
    CARRIER(ProcessMetrics),
    CARRIER(DiskUsage),
    CARRIER(PartitionList),
    CARRIER(NetInterfaceList),
    CARRIER(ContextSwitches),
};

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <expected-version> <report.json>\n", argv[0]);
        return 2;
    }
    const char *expected = argv[1];
    const char *report = argv[2];

    /* --- identity, before anything is initialised ------------------------- */
    const char *version = probe_get_version();
    record("version", version != NULL && strcmp(version, expected) == 0,
           "archive says %s, the release is %s", version ? version : "(null)", expected);

    uint64_t fingerprint = probe_get_abi_fingerprint();
    record("abi_fingerprint", fingerprint != 0, "0x%016" PRIx64, fingerprint);

    for (size_t i = 0; i < sizeof carriers / sizeof carriers[0]; i++) {
        uint64_t got = probe_get_carrier_size(carriers[i].name);
        char *label = malloc(strlen(carriers[i].name) + 9);
        if (label == NULL) {
            return 2;
        }
        sprintf(label, "carrier:%s", carriers[i].name);
        record(label, got == carriers[i].size, "archive %" PRIu64 ", header %" PRIu64, got, carriers[i].size);
    }
    /* The "unknown" answer must be the documented sentinel, not 0: a consumer
       treating 0 as a size would accept an archive that knows nothing. */
    uint64_t unknown = probe_get_carrier_size("NoSuchCarrierInProbeH");
    record("carrier:unknown-sentinel", unknown == PROBE_NOT_AVAILABLE_U64, "archive %" PRIu64, unknown);

    /* --- runtime ------------------------------------------------------------ */
    ProbeResult r = probe_init();
    record("probe_init", r.success, "%s", r.success ? "ok" : result_text(r));

    SystemCPU cpu;
    memset(&cpu, 0, sizeof cpu);
    r = probe_collect_cpu(&cpu);
    record("probe_collect_cpu", r.success && cpu.cores > 0,
           "%s, %" PRIu32 " core(s)", r.success ? "ok" : result_text(r), cpu.cores);

    SystemMemory mem;
    memset(&mem, 0, sizeof mem);
    r = probe_collect_memory(&mem);
    record("probe_collect_memory", r.success && mem.total_bytes > 0 && mem.total_bytes != PROBE_NOT_AVAILABLE_U64,
           "%s, total %" PRIu64 " bytes", r.success ? "ok" : result_text(r), mem.total_bytes);

    char *json = NULL;
    r = probe_collect_smoke_json(&json);
    int envelope = json != NULL && json[0] == '{' && strstr(json, "\"schema_version\"") != NULL;
    record("probe_collect_smoke_json", r.success && envelope, "%s, %zu byte(s)",
           r.success ? (envelope ? "ok" : "not the versioned envelope") : result_text(r), json ? strlen(json) : 0);
    probe_free_string(json);

    probe_shutdown();
    record("probe_shutdown", 1, "returned");

    /* --- report ------------------------------------------------------------- */
    int all = 1;
    for (int i = 0; i < n_checks; i++) {
        all = all && checks[i].ok;
    }
    FILE *f = fopen(report, "w");
    if (f == NULL) {
        perror(report);
        return 2;
    }
    fprintf(f, "{\"schema\":\"supervizio.libprobe-abi-report/v1\",\"expected_version\":");
    json_str(f, expected);
    fprintf(f, ",\"version\":");
    json_str(f, version);
    fprintf(f, ",\"abi_fingerprint\":\"0x%016" PRIx64 "\",\"pointer_bits\":%zu,\"checks\":[", fingerprint,
            sizeof(void *) * 8);
    for (int i = 0; i < n_checks; i++) {
        fprintf(f, "%s{\"name\":", i ? "," : "");
        json_str(f, checks[i].name);
        fprintf(f, ",\"ok\":%s,\"detail\":", checks[i].ok ? "true" : "false");
        json_str(f, checks[i].detail);
        fputc('}', f);
    }
    fprintf(f, "],\"ok\":%s}\n", all ? "true" : "false");
    if (fclose(f) != 0) {
        perror(report);
        return 2;
    }
    printf("%s: %d check(s)\n", all ? "PASS" : "FAIL", n_checks);
    return all ? 0 : 1;
}
