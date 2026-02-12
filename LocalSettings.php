<?php
/**
 * Flow Arts Wiki - MediaWiki Configuration
 *
 * Generated for Docker deployment. Database credentials
 * are injected via environment variables.
 */

# Protect against web entry
if ( !defined( 'MEDIAWIKI' ) ) {
	exit;
}

## ---------------------------------------------------------------
## Core settings
## ---------------------------------------------------------------

$wgSitename = "Flow Arts Wiki";
$wgMetaNamespace = "Flow_Arts_Wiki";
$wgServer = getenv( 'MEDIAWIKI_SERVER' ) ?: "https://flowarts.wiki";
$wgCanonicalServer = $wgServer;

# Short URLs
$wgScriptPath = "";
$wgArticlePath = "/wiki/$1";
$wgUsePathInfo = true;

# Secret keys (set in environment, fallback for initial setup)
$wgSecretKey = getenv( 'MEDIAWIKI_SECRET_KEY' ) ?: 'CHANGE_ME_AFTER_INSTALL';
$wgUpgradeKey = substr( $wgSecretKey, 0, 16 );

## ---------------------------------------------------------------
## Database
## ---------------------------------------------------------------

$wgDBtype = "mysql";
$wgDBserver = getenv( 'MEDIAWIKI_DB_HOST' ) ?: "db";
$wgDBname = getenv( 'MEDIAWIKI_DB_NAME' ) ?: "flowartswiki";
$wgDBuser = getenv( 'MEDIAWIKI_DB_USER' ) ?: "wiki";
$wgDBpassword = getenv( 'MEDIAWIKI_DB_PASSWORD' ) ?: "";
$wgDBprefix = "";
$wgDBTableOptions = "ENGINE=InnoDB, DEFAULT CHARSET=binary";

## ---------------------------------------------------------------
## Skin: Citizen
## ---------------------------------------------------------------

wfLoadSkin( 'Citizen' );
$wgDefaultSkin = "citizen";

# Citizen-specific settings
$wgCitizenEnableSearch = true;
$wgCitizenThemeDefault = "dark";
$wgCitizenEnableDrawerSiteStats = true;

## ---------------------------------------------------------------
## File uploads
## ---------------------------------------------------------------

$wgEnableUploads = true;
$wgUseImageMagick = true;
$wgImageMagickConvertCommand = "/usr/bin/convert";
$wgFileExtensions = [ 'png', 'gif', 'jpg', 'jpeg', 'svg', 'webp', 'pdf' ];
$wgMaxUploadSize = 10 * 1024 * 1024; // 10 MB

## ---------------------------------------------------------------
## Account creation and permissions
## ---------------------------------------------------------------

# Open registration with CAPTCHA
$wgGroupPermissions['*']['createaccount'] = true;
$wgGroupPermissions['*']['edit'] = false;
$wgGroupPermissions['*']['read'] = true;

# Registered users can edit
$wgGroupPermissions['user']['edit'] = true;
$wgGroupPermissions['user']['upload'] = true;
$wgGroupPermissions['user']['reupload'] = true;

# Autoconfirmed (4 days + 10 edits) get more trust
$wgAutoConfirmAge = 86400 * 4;
$wgAutoConfirmCount = 10;
$wgGroupPermissions['autoconfirmed']['move'] = true;
$wgGroupPermissions['autoconfirmed']['movefile'] = true;

## ---------------------------------------------------------------
## Anti-spam / anti-vandalism
## ---------------------------------------------------------------

wfLoadExtension( 'ConfirmEdit' );
wfLoadExtension( 'ConfirmEdit/QuestyCaptcha' );
$wgCaptchaClass = 'QuestyCaptcha';
$wgCaptchaQuestions = [
	'What type of arts does this wiki document? (two words)' => [ 'flow arts', 'Flow Arts', 'Flow arts' ],
	'Poi, staff, and fans are examples of flow arts ____?' => [ 'props', 'Props' ],
];
$wgCaptchaTriggers['edit'] = false;
$wgCaptchaTriggers['create'] = false;
$wgCaptchaTriggers['createaccount'] = true;
$wgCaptchaTriggers['addurl'] = true;

wfLoadExtension( 'AbuseFilter' );
$wgGroupPermissions['sysop']['abusefilter-modify'] = true;
$wgGroupPermissions['sysop']['abusefilter-view'] = true;
$wgGroupPermissions['sysop']['abusefilter-log'] = true;

## ---------------------------------------------------------------
## Extensions
## ---------------------------------------------------------------

wfLoadExtension( 'Cite' );
wfLoadExtension( 'CiteThisPage' );
wfLoadExtension( 'CategoryTree' );
wfLoadExtension( 'ParserFunctions' );
$wgPFEnableStringFunctions = true;
wfLoadExtension( 'Scribunto' );
$wgScribuntoDefaultEngine = 'luastandalone';
wfLoadExtension( 'VisualEditor' );
wfLoadExtension( 'LinkHealth' );

# VisualEditor: use Parsoid bundled with MW 1.43
$wgVisualEditorAvailableNamespaces = [
	NS_MAIN => true,
	NS_PROJECT => true,
	NS_HELP => true,
];
$wgDefaultUserOptions['visualeditor-enable'] = 1;
$wgDefaultUserOptions['visualeditor-editor'] = "visualeditor";

## ---------------------------------------------------------------
## Performance
## ---------------------------------------------------------------

# Object cache (APCu in container)
$wgMainCacheType = CACHE_ACCEL;
$wgSessionCacheType = CACHE_DB;
$wgMemCachedServers = [];

# Parser cache
$wgParserCacheType = CACHE_DB;
$wgCacheDirectory = "$IP/cache";

# Job runner: defer jobs to post-request
$wgJobRunRate = 0.01;

## ---------------------------------------------------------------
## Email (disabled initially)
## ---------------------------------------------------------------

$wgEnableEmail = false;
$wgEnableUserEmail = false;
$wgEnotifUserTalk = false;
$wgEnotifWatchlist = false;

## ---------------------------------------------------------------
## Branding
## ---------------------------------------------------------------

$wgLogos = [
	'icon' => "/favicon.svg",
	'wordmark' => [
		'src' => "/favicon.svg",
		'width' => 135,
		'height' => 20,
	],
];
$wgFavicon = "/favicon.svg";

## ---------------------------------------------------------------
## Miscellaneous
## ---------------------------------------------------------------

$wgLanguageCode = "en";
$wgLocaltimezone = "UTC";
$wgRightsPage = "";
$wgRightsUrl = "https://creativecommons.org/licenses/by-sa/4.0/";
$wgRightsText = "Creative Commons Attribution-ShareAlike 4.0";
$wgRightsIcon = "https://licensebuttons.net/l/by-sa/4.0/88x31.png";

# Allow subpages in main namespace (useful for notation documentation)
$wgNamespacesWithSubpages[NS_MAIN] = true;

# Debug (disable in production)
$wgShowExceptionDetails = true;
$wgShowDBErrorBacktrace = true;
