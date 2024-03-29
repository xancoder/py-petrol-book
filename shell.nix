let
  pkgs = import <nixpkgs> {
    config = { allowUnfree = true; };
  };
in
pkgs.mkShell {
  name="run-py-petrol-book";
  packages = with pkgs; [
    python311
    python311Packages.streamlit
  ];
  shellHook = ''
streamlit run py_petrol_book/app.py
'';
}
