#include "HttpDownload.h"

#include <windows.h>
#include <winhttp.h>
#include <iostream>
#include <fstream>
#include "Utils\StringUtils.h"

namespace Web
{
    int DownloadFile( const std::string& inServer, const std::string& inPath, const Path& outPath )
    {
        // Initialize WinHTTP session
        HINTERNET hSession = WinHttpOpen( L"A WinHTTP Example/1.0",
            WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
            WINHTTP_NO_PROXY_NAME,
            WINHTTP_NO_PROXY_BYPASS, 0 );

        if( !hSession ) {
            std::cerr << "Failed to open WinHTTP session." << std::endl;
            return 1;
        }

        // Specify the server to connect to
        HINTERNET hConnect = WinHttpConnect( hSession, StringUtils::ToWString( inServer ).c_str(),
            INTERNET_DEFAULT_HTTPS_PORT, 0 );

        if( !hConnect ) {
            std::cerr << "Failed to connect to the server." << std::endl;
            WinHttpCloseHandle( hSession );
            return 1;
        }

        // Create an HTTP request handle
        HINTERNET hRequest = WinHttpOpenRequest( hConnect, L"GET", StringUtils::ToWString( inPath ).c_str(),
            NULL, WINHTTP_NO_REFERER,
            WINHTTP_DEFAULT_ACCEPT_TYPES,
            WINHTTP_FLAG_SECURE );

        if( !hRequest ) {
            std::cerr << "Failed to open HTTP request." << std::endl;
            WinHttpCloseHandle( hConnect );
            WinHttpCloseHandle( hSession );
            return 1;
        }

        // Send the HTTP request
        if( !WinHttpSendRequest( hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
            WINHTTP_NO_REQUEST_DATA, 0, 0, 0 ) ) {
            std::cerr << "Failed to send request." << std::endl;
        }

        // Receive the response
        if( !WinHttpReceiveResponse( hRequest, NULL ) ) {
            std::cerr << "Failed to receive response." << std::endl;
        }

        if( !std::filesystem::exists( outPath.GetDirectoryString() ) ) {
            std::filesystem::create_directories( outPath.GetDirectoryString() );
        }

        // Read the data
        DWORD dwSize = 0;
        DWORD dwDownloaded = 0;
        std::ofstream outfile( outPath.FullPath.c_str(), std::ios::binary );
        if( outfile.is_open() ) {
            do {
                // Check for available data
                dwSize = 0;
                WinHttpQueryDataAvailable( hRequest, &dwSize );

                if( dwSize == 0 )
                    break;

                // Allocate buffer for data
                char* buffer = new char[dwSize];

                // Read data
                if( WinHttpReadData( hRequest, (LPVOID)buffer, dwSize, &dwDownloaded ) ) {
                    outfile.write( buffer, dwDownloaded );
                }

                delete[] buffer;
            } while( dwSize > 0 );

            outfile.close();
        }
        else {
            std::cerr << "Failed to open output file." << std::endl;
        }

        // Clean up
        WinHttpCloseHandle( hRequest );
        WinHttpCloseHandle( hConnect );
        WinHttpCloseHandle( hSession );

        std::cout << "File downloaded successfully.\n";
        return 0;
    }

}