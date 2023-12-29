let
  pkgs = import <nixpkgs> {
    config = { allowUnfree = true; };
  };
in
pkgs.mkShell {
  name="dev-env-youtube-grabber";
  packages = with pkgs; [
    git
    jetbrains.pycharm-professional
    poetry
    python311
    python311Packages.pip
    python311Packages.streamlit
  ];
  shellHook = ''
echo "enjoy developing"
which poetry
which python
pycharm-professional
'';
}
