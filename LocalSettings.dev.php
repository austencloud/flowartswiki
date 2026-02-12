<?php
/**
 * Flow Arts Wiki - Local Development Configuration
 *
 * Uses SQLite (no MariaDB needed) and PHP's built-in server.
 * Run: php -S localhost:8080 -t wiki wiki/router.php
 */

if ( !defined( 'MEDIAWIKI' ) ) {
	exit;
}

## Core
$wgSitename = "Flow Arts Wiki";
$wgMetaNamespace = "Flow_Arts_Wiki";
$wgServer = "http://localhost:8080";

$wgScriptPath = "";
$wgArticlePath = "/wiki/$1";
$wgUsePathInfo = true;

$wgSecretKey = "dev-only-not-for-production-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
$wgUpgradeKey = substr( $wgSecretKey, 0, 16 );

## SQLite (no MariaDB needed)
$wgDBtype = "sqlite";
$wgDBname = "flowartswiki";
$wgSQLiteDataDir = "$IP/data";

## Skin: Vector 2022 (bundled with MediaWiki)
$wgDefaultSkin = "vector-2022";

## Uploads
$wgEnableUploads = true;
$wgFileExtensions = [ 'png', 'gif', 'jpg', 'jpeg', 'svg', 'webp', 'pdf' ];
$wgMaxUploadSize = 10 * 1024 * 1024;

## Permissions (mirrors production)
$wgGroupPermissions['*']['createaccount'] = true;
$wgGroupPermissions['*']['edit'] = false;
$wgGroupPermissions['*']['read'] = true;
$wgGroupPermissions['user']['edit'] = true;
$wgGroupPermissions['user']['upload'] = true;
$wgGroupPermissions['user']['reupload'] = true;

## Extensions (bundled ones only - no Lua or Parsoid needed)
wfLoadExtension( 'Cite' );
wfLoadExtension( 'CiteThisPage' );
wfLoadExtension( 'CategoryTree' );
wfLoadExtension( 'ParserFunctions' );
$wgPFEnableStringFunctions = true;

## Cache (none for dev - no APCu needed)
$wgMainCacheType = CACHE_NONE;
$wgCacheDirectory = "$IP/cache";

## Dev: show errors
$wgShowExceptionDetails = true;
$wgShowDBErrorBacktrace = true;

## Email off
$wgEnableEmail = false;

## Misc
$wgLanguageCode = "en";
$wgLocaltimezone = "UTC";
$wgRightsUrl = "https://creativecommons.org/licenses/by-sa/4.0/";
$wgRightsText = "Creative Commons Attribution-ShareAlike 4.0";
$wgNamespacesWithSubpages[NS_MAIN] = true;

## Branding
$wgFavicon = "/favicon.svg";
