#pragma once
#include "Path.h"

namespace Web
{
    int DownloadFile( const std::string& inServer, const std::string& inPath, const Path& outPath );
}