<?php

	class action implements actionInterface {
		
		function doDownloading() {
			
			$buttons = [
			['name' => 'Delete', 'class' => 'button_delete'],
			['name' => 'Reset', 'class' => 'button_reset'],
			];

			$buttonsHTML = createButtons($buttons);
			
			echo "<h2>Currently Downloading</h2>";
			echo $buttonsHTML;
			echo "<div class='downloads' getType='2' action='downloads'></div>";
			echo $buttonsHTML;
							
		}
		
		function doQueue() {
			
			$buttons = [
			['name' => 'Delete', 'class' => 'button_delete'],
			['name' => 'Make Priority', 'class' => 'button_priority'],
			];
			
			$buttonsHTML = createButtons($buttons);
			
			echo "<h2>In Queue</h2>";
			echo $buttonsHTML;
			echo "<div class='downloads' getType='1' action='downloads'></div>";
			echo $buttonsHTML;
		}
		
		function doPending() {
			
			$buttons = [
				['name' => 'Delete', 'class' => 'button_delete'],
				['name' => 'Approve', 'class' => 'button_approve'],
				['name' => 'Ignore', 'class' => 'button_ignore'],
				['name' => 'Approve & Get More', 'class' => 'button_approvemore'],
			];
			
			$buttonsHTML = createButtons($buttons);
			
			echo "<h2>Pending Approvals</h2>";
			echo $buttonsHTML;
			echo "<div class='downloads' getType='6' action='downloads'></div>";
			echo $buttonsHTML;
		}
		
		function doErrors() {
			
			$buttons = [
			['name' => 'Delete', 'class' => 'button_delete'],
			['name' => 'Retry', 'class' => 'button_retry'],
			['name' => 'Sort Special', 'class' => 'button_page_special'],
			];
			
			$buttonsHTML = createButtons($buttons);
			
			echo "<h2>Failed Downloads</h2>";
			echo $buttonsHTML;
			echo "<div class='downloads' getType='3' action='downloads'></div>";
			echo $buttonsHTML;
		}
		
		function doSpecials() {
				
			$buttons = [
			['name' => 'Save', 'class' => 'button_savespecial'],
			];
				
			$buttonsHTML = createButtons($buttons);
				
			$ids = '';
			$i = 1;
			foreach($_GET['id'] as $id) {
				if ($i == 1) {
					$ids .= "$id";
				} else {
					$ids .= ",$id";
				}
				$i++;
			}
			
			
			
			echo "<h2>Manually Sort Specials</h2>";
			echo $buttonsHTML;
			echo "<div class='downloads' getType='10' ids='$ids' action='downloads'></div>";
			echo $buttonsHTML;
		}
		
		function doArchive() {
			echo "<h2>Recent Downloads</h2>";
			echo "<div class='downloads' getType='4' action='downloads'></div>";
			echo "<div id='buttons'><a class='button' href=''><span>Delete</span></a></div>";
		}

		
		function getBody() {
			
			if (array_key_exists('t', $_GET)){
				if ($_GET['t'] == "d") {
					$this->doDownloading();
				} else if ($_GET['t'] == "q") {
					$this->doQueue();
				} else if ($_GET['t'] == "p") {
					$this->doPending();
				} else if ($_GET['t'] == "e") {
					$this->doErrors();
				} else if ($_GET['t'] == "a") {
					$this->doArchive();
				} else if ($_GET['t'] == "special") {
					$this->doSpecials();
				}
			} else {
				$this->doDownloading();
			}
			

		}
		
	
		function getSubMenu() {
			echo '
				<ul id="page-actions2">
					<li><a href="/index.php?action=downloads&t=d">Downloading</a></li>
					<li><a href="/index.php?action=downloads&t=q">Queue</a></li>
					<li><a href="/index.php?action=downloads&t=p">Pending Approval</a></li>
					<li><a href="/index.php?action=downloads&t=e">Errors</a></li>
					<li><a href="/index.php?action=downloads&t=a">Recent</a></li>
				</ul>';
		}
		
		function getHeader() {
			echo '';
		}
		
	}
?>