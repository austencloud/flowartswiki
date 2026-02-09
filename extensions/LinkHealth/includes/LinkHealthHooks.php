<?php
namespace MediaWiki\Extension\LinkHealth;

use MediaWiki\Revision\RevisionRecord;
use MediaWiki\Storage\EditResult;
use MediaWiki\User\UserIdentity;
use WikiPage;

/**
 * PageSaveComplete hook: extract external URLs from saved pages
 * and queue them for the LinkKeeper container to process.
 */
class LinkHealthHooks {

	/**
	 * @param WikiPage $wikiPage
	 * @param UserIdentity $user
	 * @param string $summary
	 * @param int $flags
	 * @param RevisionRecord $revisionRecord
	 * @param EditResult $editResult
	 */
	public static function onPageSaveComplete(
		WikiPage $wikiPage,
		UserIdentity $user,
		string $summary,
		int $flags,
		RevisionRecord $revisionRecord,
		EditResult $editResult
	): void {
		$content = $revisionRecord->getContent( \MediaWiki\Revision\SlotRecord::MAIN );
		if ( !$content ) {
			return;
		}

		$text = $content->serialize();
		$pageId = $wikiPage->getId();

		// Extract all http/https URLs from the page content
		$urls = self::extractUrls( $text );
		if ( empty( $urls ) ) {
			return;
		}

		$dbw = \MediaWiki\MediaWikiServices::getInstance()
			->getDBLoadBalancer()
			->getConnection( DB_PRIMARY );

		$timestamp = wfTimestampNow();

		foreach ( $urls as $url ) {
			// Skip internal wiki URLs
			if ( self::isInternalUrl( $url ) ) {
				continue;
			}

			$dbw->insert(
				'faw_link_queue',
				[
					'lq_url' => $url,
					'lq_page_id' => $pageId,
					'lq_timestamp' => $timestamp,
					'lq_action' => 'discover',
				],
				__METHOD__,
				[ 'IGNORE' ]
			);
		}
	}

	/**
	 * Extract external URLs from wikitext.
	 */
	private static function extractUrls( string $text ): array {
		$urls = [];

		// Match [http://...] and [https://...] external links
		// Match bare http:// and https:// URLs
		// Match url= parameters in templates
		preg_match_all(
			'/https?:\/\/[^\s\|\]\}\)<>"\']+/',
			$text,
			$matches
		);

		if ( !empty( $matches[0] ) ) {
			foreach ( $matches[0] as $url ) {
				// Trim trailing punctuation that's likely not part of the URL
				$url = rtrim( $url, '.,;:!?)' );
				$urls[] = $url;
			}
		}

		return array_unique( $urls );
	}

	/**
	 * Check if a URL points to this wiki.
	 */
	private static function isInternalUrl( string $url ): bool {
		$server = \MediaWiki\MediaWikiServices::getInstance()
			->getMainConfig()
			->get( 'Server' );
		$serverHost = parse_url( $server, PHP_URL_HOST );
		$urlHost = parse_url( $url, PHP_URL_HOST );

		return $serverHost && $urlHost && strcasecmp( $serverHost, $urlHost ) === 0;
	}
}
