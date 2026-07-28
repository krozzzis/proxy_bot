{
  description = "proxy_bot - Telegram bot for handing out access via codes";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.python312
            pkgs.uv
            # rsvg-convert, used by scripts/generate_emoji_pack.py to render
            # the custom-emoji icon pack from SVG to PNG.
            pkgs.librsvg
          ];

          env = {
            UV_PYTHON = "${pkgs.python312}/bin/python3.12";
            UV_PYTHON_DOWNLOADS = "never";
          };

          shellHook = ''
            export UV_PYTHON="${pkgs.python312}/bin/python3.12"
            export UV_PYTHON_DOWNLOADS=never
            echo "proxy_bot dev shell: python $(python3 --version), uv $(uv --version)"
            echo "Run 'uv sync' then 'uv run proxy-bot' to start the bot."
          '';
        };
      });
}
