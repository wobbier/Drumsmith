# Private game dependencies extend the SDK's pinned environment.
{ pkgs }:
{
  packages = [ pkgs.nodejs_26 ];
  buildInputs = [ pkgs.alsa-lib ];
  runtimeLibraries = [ pkgs.alsa-lib ];
}
