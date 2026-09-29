# e2e.yml's nixos-nix legs: the NixOS system they boot in a container.
#
# supervizio's flake is imported the way its README tells users to
# (github:supervizio/nix-supervizio, nixpkgs following the host's). The legs
# never fetch that: they pass --override-input supervizio path:<dir> with the
# flake agent's setup/packaging/render-channels.py wrote for the binaries
# under test, which is what agent's deploy-repo.yml would publish for them.
#
# Two configurations in one system closure:
#   * the base boots first -- no supervizio;
#   * specialisation "supervizio" enables services.supervizio. Switching to it
#     (switch-to-configuration test) is the install, done by NixOS's own
#     activation, and switching back to the base is the removal.
{
  inputs = {
    # nixos-26.05 as of 2026-09-27: every run boots the same system.
    nixpkgs.url = "github:NixOS/nixpkgs/cf5e76507c6e23b59f7e0ffcc7baa2a39ddd8442";
    supervizio = {
      url = "github:supervizio/nix-supervizio";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { nixpkgs, supervizio, ... }:
    let
      leg =
        system:
        nixpkgs.lib.nixosSystem {
          inherit system;
          modules = [
            supervizio.nixosModules.default
            (
              { lib, pkgs, ... }:
              {
                # A container: no kernel, no boot loader; systemd is PID 1
                # through NixOS's own stage 2 (the system's `init`).
                boot.isContainer = true;
                networking.hostName = "svz-nixos";
                # The container runs unprivileged, like every other container
                # leg (no added capability, Docker's AppArmor profile). What
                # stock NixOS needs beyond that is switched off here, and none
                # of it is supervizio's:
                #   resolvconf   fails on Docker's read-only /etc/resolv.conf;
                #   nscd         (nsncd) must keep CAP_SYS_ADMIN, and cannot;
                #   dbus-broker  exits at start ("launcher_run_child ...
                #                Package not installed"), and
                #                switch-to-configuration has no bus without
                #                it: the reference dbus-daemon runs as is;
                #   oomd, the setuid wrappers  a PSI reader and a tmpfs mount
                #                the container does not grant;
                #   special filesystems  Docker already mounts /proc, /sys,
                #                /dev, /dev/pts, /dev/shm, and the leg /run;
                #                remounting them needs CAP_SYS_ADMIN, and the
                #                activation's `specialfs` snippet then fails
                #                every switch.
                # Measured on both runners: stock, the system boots "degraded"
                # and cannot switch; running it anyway would take --cap-add
                # SYS_ADMIN and AppArmor off, which lets root in the container
                # reach the runner.
                networking.resolvconf.enable = false;
                services.nscd.enable = false;
                system.nssModules = lib.mkForce [ ];
                services.dbus.implementation = "dbus";
                systemd.oomd.enable = false;
                security.enableWrappers = false;
                boot.specialFileSystems = lib.mkForce { };
                # Manuals are most of a closure nobody reads here.
                documentation.enable = false;
                # agent's validate-probe.sh and validate-detection.sh need jq,
                # its scenario battery needs pgrep.
                environment.systemPackages = [
                  pkgs.jq
                  pkgs.procps
                ];
                system.stateVersion = "26.05";

                specialisation.supervizio.configuration.services.supervizio.enable = true;
              }
            )
          ];
        };
    in
    {
      nixosConfigurations.x86_64-linux = leg "x86_64-linux";
      nixosConfigurations.aarch64-linux = leg "aarch64-linux";
    };
}
