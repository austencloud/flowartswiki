<?php
namespace MediaWiki\Extension\LinkHealth;

use SpecialPage;
use Html;

/**
 * Special:LinkHealth - Read-only dashboard showing external link health.
 *
 * Displays summary stats, dead links table, and per-domain health.
 * All data comes from faw_link_archive, populated by the LinkKeeper container.
 */
class SpecialLinkHealth extends SpecialPage {

	public function __construct() {
		parent::__construct( 'LinkHealth' );
	}

	public function getGroupName(): string {
		return 'wiki';
	}

	public function execute( $sub ): void {
		$this->setHeaders();
		$this->outputHeader();

		$out = $this->getOutput();
		$out->addModuleStyles( 'mediawiki.special' );

		$dbr = \MediaWiki\MediaWikiServices::getInstance()
			->getDBLoadBalancer()
			->getConnection( DB_REPLICA );

		// Check if tables exist
		if ( !$dbr->tableExists( 'faw_link_archive' ) ) {
			$out->addWikiTextAsInterface(
				'{{Warning|LinkKeeper tables not found. Run <code>scripts/linkkeeper/setup-db.sh</code> first.}}'
			);
			return;
		}

		$this->showSummary( $out, $dbr );
		$this->showDeadLinks( $out, $dbr );
		$this->showDomainHealth( $out, $dbr );
	}

	private function showSummary( $out, $dbr ): void {
		$stats = [];
		$stats['linkhealth-total'] = (int)$dbr->selectField( 'faw_link_archive', 'COUNT(*)' );
		$stats['linkhealth-dead'] = (int)$dbr->selectField( 'faw_link_archive', 'COUNT(*)', [ 'la_is_dead' => 1 ] );
		$stats['linkhealth-archived'] = (int)$dbr->selectField( 'faw_link_archive', 'COUNT(*)', 'la_wayback_url IS NOT NULL' );
		$stats['linkhealth-snapshotted'] = (int)$dbr->selectField( 'faw_link_archive', 'COUNT(*)', 'la_r2_key IS NOT NULL' );
		$stats['linkhealth-remediated'] = (int)$dbr->selectField( 'faw_link_archive', 'COUNT(*)', [ 'la_remediated' => 1 ] );
		$stats['linkhealth-queued'] = (int)$dbr->selectField( 'faw_link_queue', 'COUNT(*)' );
		$stats['linkhealth-domains'] = (int)$dbr->selectField( 'faw_link_archive', 'COUNT(DISTINCT la_domain)' );

		$html = Html::openElement( 'table', [ 'class' => 'wikitable' ] );
		foreach ( $stats as $msgKey => $value ) {
			$html .= Html::rawElement( 'tr', [],
				Html::element( 'th', [], $this->msg( $msgKey )->text() ) .
				Html::element( 'td', [], (string)$value )
			);
		}
		$html .= Html::closeElement( 'table' );

		$out->addHTML( $html );
	}

	private function showDeadLinks( $out, $dbr ): void {
		$out->addHTML( Html::element( 'h2', [], $this->msg( 'linkhealth-dead-links-title' )->text() ) );

		$rows = $dbr->select(
			'faw_link_archive',
			[ 'la_url', 'la_http_status', 'la_dead_since', 'la_consecutive_failures', 'la_wayback_url', 'la_domain' ],
			[ 'la_is_dead' => 1 ],
			__METHOD__,
			[ 'ORDER BY' => 'la_dead_since DESC', 'LIMIT' => 100 ]
		);

		if ( $rows->numRows() === 0 ) {
			$out->addWikiTextAsInterface( $this->msg( 'linkhealth-no-dead-links' )->text() );
			return;
		}

		$html = Html::openElement( 'table', [ 'class' => 'wikitable sortable' ] );
		$html .= Html::rawElement( 'tr', [],
			Html::element( 'th', [], $this->msg( 'linkhealth-url' )->text() ) .
			Html::element( 'th', [], $this->msg( 'linkhealth-status' )->text() ) .
			Html::element( 'th', [], $this->msg( 'linkhealth-dead-since' )->text() ) .
			Html::element( 'th', [], $this->msg( 'linkhealth-failures' )->text() ) .
			Html::element( 'th', [], $this->msg( 'linkhealth-archive' )->text() )
		);

		foreach ( $rows as $row ) {
			$url = $row->la_url;
			$archiveLink = '';
			if ( $row->la_wayback_url ) {
				$archiveLink = Html::element( 'a', [
					'href' => $row->la_wayback_url,
					'rel' => 'nofollow',
				], $this->msg( 'linkhealth-view-archive' )->text() );
			}

			$deadSince = $row->la_dead_since
				? substr( $row->la_dead_since, 0, 4 ) . '-' .
				  substr( $row->la_dead_since, 4, 2 ) . '-' .
				  substr( $row->la_dead_since, 6, 2 )
				: '';

			$html .= Html::rawElement( 'tr', [],
				Html::rawElement( 'td', [],
					Html::element( 'a', [ 'href' => $url, 'rel' => 'nofollow' ],
						strlen( $url ) > 60 ? substr( $url, 0, 57 ) . '...' : $url
					)
				) .
				Html::element( 'td', [], (string)$row->la_http_status ) .
				Html::element( 'td', [], $deadSince ) .
				Html::element( 'td', [], (string)$row->la_consecutive_failures ) .
				Html::rawElement( 'td', [], $archiveLink )
			);
		}

		$html .= Html::closeElement( 'table' );
		$out->addHTML( $html );
	}

	private function showDomainHealth( $out, $dbr ): void {
		$out->addHTML( Html::element( 'h2', [], $this->msg( 'linkhealth-domain-health-title' )->text() ) );

		$rows = $dbr->select(
			'faw_link_archive',
			[
				'la_domain',
				'total' => 'COUNT(*)',
				'healthy' => 'SUM(CASE WHEN la_is_dead = 0 THEN 1 ELSE 0 END)',
			],
			[],
			__METHOD__,
			[
				'GROUP BY' => 'la_domain',
				'ORDER BY' => 'total DESC',
				'LIMIT' => 50,
			]
		);

		$html = Html::openElement( 'table', [ 'class' => 'wikitable sortable' ] );
		$html .= Html::rawElement( 'tr', [],
			Html::element( 'th', [], $this->msg( 'linkhealth-domain' )->text() ) .
			Html::element( 'th', [], $this->msg( 'linkhealth-count' )->text() ) .
			Html::element( 'th', [], $this->msg( 'linkhealth-healthy' )->text() ) .
			Html::element( 'th', [], $this->msg( 'linkhealth-dead' )->text() )
		);

		foreach ( $rows as $row ) {
			$dead = $row->total - $row->healthy;
			$html .= Html::rawElement( 'tr', [],
				Html::element( 'td', [], $row->la_domain ) .
				Html::element( 'td', [], (string)$row->total ) .
				Html::element( 'td', [], (string)$row->healthy ) .
				Html::element( 'td', [], (string)$dead )
			);
		}

		$html .= Html::closeElement( 'table' );
		$out->addHTML( $html );
	}
}
