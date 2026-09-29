<!-- updated: 2026-09-29T00:00:00Z -->
# .github/nixos-leg/

`flake.nix` is the NixOS 26.05 system `e2e.yml`'s `e2e-linux-nixos-nix` legs
build and boot, `x86_64-linux` and `aarch64-linux`.

- It imports supervizio's flake the way that flake's README tells users to
  (`github:supervizio/nix-supervizio`, nixpkgs following), and the legs always
  replace it with `--override-input supervizio path:<dir>`: the flake agent's
  `setup/packaging/render-channels.py` wrote for the binaries under test.
  Nothing is fetched from the published repository.
- One closure, two configurations: the base (no supervizio), which the
  container boots, and `specialisation.supervizio` with
  `services.supervizio.enable = true`. Installing is
  `switch-to-configuration test` into the specialisation, removing is switching
  back: NixOS's own activation, both ways.
- The container is unprivileged, like every other container leg (no added
  capability, Docker's AppArmor profile), because candidate bytes run in it as
  root. What stock NixOS needs beyond that is switched off in `flake.nix`, each
  with its reason: resolvconf, nscd (and its NSS modules), dbus-broker (the
  reference dbus-daemon instead), oomd, the setuid wrappers, and the special
  filesystems Docker already mounts. Measured on both runners: stock, the
  system boots degraded and cannot switch; running it anyway would take
  `--cap-add SYS_ADMIN` with AppArmor off, a way from container root to the
  runner. None of it touches `services.supervizio`.
- `boot.isContainer`, `documentation.enable = false`, and `jq` + `procps` for
  agent's validators and battery.
- nixpkgs is pinned to a nixos-26.05 commit, so every run boots the same
  system. Moving it is a change here, proven by a run of both legs.

No lock file: nixpkgs is pinned by commit in the URL and the supervizio input
is always overridden. The legs pass `--no-write-lock-file`.
