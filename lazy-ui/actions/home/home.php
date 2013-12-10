<?php


class action implements actionInterface {
	
	function getCount($id, $where) {
		global $db;
		$sql = "SELECT count(*) FROM download WHERE status = $id $where";
		
		$result = $db->query($sql);
		
		$rowCount = $result->fetch(PDO::FETCH_NUM);
		
		return $rowCount[0];
	}
	
	function getBody() {
		global $config;
		
		//get stats
		$downloading = $this->getCount(2, '');
		$extracting = $this->getCount(3, 'and message = ""');
		$queue = $this->getCount(1, '');
		$pending = $this->getCount(6, '');
		$errors = $this->getCount(3, 'and message != ""');
		
		$df = disk_free_space($config::$tvshowsPath);
		$dt = disk_total_space($config::$tvshowsPath);
		
		$gbFree = number_format($df / 1024 / 1024 / 1024, 2);		
		$percentUsed = number_format(100 - ($dt / $df), 2);
		
		
		$html = "<h3>Media Server Status</h3>
				<div class='stats'>
					<div class='left'>
						<div class='stat'><a href='/index.php?action=downloads&t=d'><img src='/images/icons/download.jpg'></a>Downloading <strong>$downloading</strong> items</div>
						<div style='clear:both'></div>
						<div class='stat'><a href='index.php?action=downloads&t=q'><img src='/images/icons/download_queue.jpg'></a>Queue <strong>$queue</strong> items</div>
						<div style='clear:both'></div>
						<div class='stat'><a href='/index.php?action=downloads&t=p'><img src='/images/icons/approval.jpg'></a>Waiting Approval (Pending) <strong>$pending</strong></div>
						<div style='clear:both'></div>
					</div>
					<div class='right'>						
						<div class='stat'>
								<div class='progressbar_10'></div>
								<div class='middle'><strong>$percentUsed% Used ($gbFree GB Free)</strong></div>
							<script>doReverseProgressbar(10, $percentUsed)</script>
						</div>
						<div style='clear:both'></div>
						<div class='stat'><img src='/images/icons/extracting.png'>Extracting <strong>$extracting</strong></div>
						<div style='clear:both'></div>
						<div class='stat'><a href='/index.php?action=downloads&t=e'><img src='/images/icons/error.jpg'></a>Errors: <strong>$errors</strong></div>
						<div style='clear:both'></div>
					</div>
		
				
			    </div>";
		
		echo $html;
	}
	
	
	function getSubMenu() {
		echo '';
	}
	
	function getHeader() {
		echo '';
	}
	
}


?>

