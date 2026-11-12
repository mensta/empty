// Prints one Urban VPN HTTP proxy URL (Japan servers only) to stdout. Everything else goes to stderr.
//
// Usage: node urban_proxy.mjs [--exclude name,name] [--tries 5]
//
// - Only accessible servers in country JP are used. There is no fallback to other countries:
//   SUUMO and HOME'S reject non-Japanese exits (503 / 403).
// - Each candidate is checked with an HTTP CONNECT to suumo.jp:443 before it is returned.
// - The URL contains a credential. Never log it or commit it.
// - @becauseyes/urbanvpn-api-wrapper is AGPL-3.0. It is used only here, as a separate process.
import http from "node:http";
import {
  AccountService,
  SecurityService,
  StaticProxiesService,
} from "@becauseyes/urbanvpn-api-wrapper";

const COUNTRY = "JP";
const CHECK_TARGET = "suumo.jp:443";

function parseArgs(argv) {
  const out = { exclude: [], tries: 5 };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--exclude") out.exclude = (argv[++i] ?? "").split(",").filter(Boolean);
    else if (argv[i] === "--tries") out.tries = Number(argv[++i]);
    else throw new Error(`unknown argument: ${argv[i]}`);
  }
  if (!Number.isInteger(out.tries) || out.tries < 1) throw new Error("--tries must be a positive integer");
  return out;
}

// Returns a promise that resolves if the proxy answers CONNECT with 200 within the timeout.
function checkProxy(host, port, token, target = CHECK_TARGET, timeoutMs = 8000) {
  const auth = Buffer.from(`${token}:1`).toString("base64");
  return new Promise((resolve, reject) => {
    const req = http.request({
      host,
      port,
      method: "CONNECT",
      path: target,
      headers: { Host: target, "Proxy-Authorization": `Basic ${auth}` },
    });
    const fail = (msg) => {
      req.destroy();
      reject(new Error(msg));
    };
    req.setTimeout(timeoutMs, () => fail(`timed out after ${timeoutMs}ms`));
    req.on("error", (e) => fail(e.message));
    req.on("connect", (res, socket) => {
      socket.destroy();
      if (res.statusCode === 200) resolve();
      else fail(`CONNECT ${target} returned ${res.statusCode}`);
    });
    req.end();
  });
}

async function main() {
  const { exclude, tries } = parseArgs(process.argv.slice(2));

  const account = await new AccountService().registerAnonymous();
  const security = new SecurityService();
  const { value: securityToken } = await security.getSecurityToken(account.value);
  const countries = await new StaticProxiesService(securityToken).getCountries();

  const country = countries.elements.find((c) => c.code.iso2 === COUNTRY);
  const servers = (country?.servers?.elements ?? []).filter(
    (s) => s.accessType !== "INACCESSIBLE" && !exclude.includes(s.name)
  );
  if (servers.length === 0) {
    throw new Error(`no accessible ${COUNTRY} server (excluded: ${exclude.join(",") || "none"})`);
  }

  // Shuffle so repeated runs spread over the servers, then try the lightest ones first.
  for (let i = servers.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [servers[i], servers[j]] = [servers[j], servers[i]];
  }
  servers.sort((a, b) => a.weight - b.weight);

  let lastError = "no candidate";
  for (const server of servers.slice(0, tries)) {
    const addr = server.address.primary;
    const host = addr.ip || addr.host;
    try {
      // The signature is shared by all addresses of the server (same as get-yt-yay).
      const auth = await security.getAuthProxyToken(securityToken, server.signature);
      await checkProxy(host, addr.port, auth.value);
      console.error(`urban proxy: ${server.name} ${host}:${addr.port} (${COUNTRY})`);
      process.stdout.write(`http://${encodeURIComponent(auth.value)}:1@${host}:${addr.port}\n`);
      return;
    } catch (e) {
      lastError = `${server.name}: ${e.message}`;
      console.error(`urban proxy: skipped ${lastError}`);
    }
  }
  throw new Error(`no working ${COUNTRY} server (${lastError})`);
}

main().catch((e) => {
  console.error(`urban proxy failed: ${e.message}`);
  process.exit(1);
});
