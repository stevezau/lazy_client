<?php

include_once '../../includes/functions.php';
include_once '../../includes/TVDB.php';

global $db;

switch ($_GET['action']) {
	
	case "addshowmapping":
		$title = htmlspecialchars_decode($_POST['smapTitle']);
		$id = $_POST['item'];
		
		$title = removeIllegalChars($title);
		
		$config->addShowMapping($title, $id);
		
		echo "Mapped title: $title to TheTVDB show id: $id";
		
		break;
	case "addshow":
		global $config;
		
		if($_POST['item']){
				
			$tvdbusr = new TV_User();
			$tvdb = new TV_Shows();
				
			foreach($_POST['item'] as $id){
				$tvdbusr->addFav($id, $config::$tvdbAccountID);
				
				//add to the master tvdb account
				$tvdbusr->addFav($id, '289F895955772DE3');
				
				//Also add it to the master download tv record
				$tvdbusr = new TV_User();
				
				$tvshow = $tvdb->findById($id);
				
				$title = $tvshow->seriesName;
				
				$title = removeIllegalChars($title);
				
				//Now create the folder
				mkdir('/data/Videos/TVShows/' . $title);
			}
			echo 'Adding Success - it may take 10-20mins for it to show up!';
				
		}		
		
		break;
		
	case 'deletemapping':
		global $config;
		
		if (array_key_exists('item', $_POST)) {
		
			foreach($_POST['item'] as $title){
				
				$title = removeIllegalChars($title);
				
				//delete each $i with $i being the id
				$config::removeShowMapping($title);
			}
			echo 'Delete Success';
		
		}
		break;
		
	case "delete":
		global $config;

		if (array_key_exists('item', $_POST)) {
								
			$tvdbusr = new TV_User();
				
			foreach($_POST['item'] as $id){
				//delete each $i with $i being the id
				$tvdbusr->deleteFav($id, $config::$tvdbAccountID);
			}
			echo 'Delete Success';
	
		}
			
		if (array_key_exists('manitemIgnore', $_POST)) {
			foreach($_POST['manitemIgnore'] as $title){
				delFromFile($title, $config::$ignore_file);
			}
			echo 'Delete Success';
		}
	
		if (array_key_exists('manitem', $_POST)) {
			foreach($_POST['manitem'] as $title){
				delFromFile($title, $config::$approved_file);
			}	
			echo 'Delete Success';
		}
					
		break;
		

	default:
		echo 'UNKNWON COMMAND';
}
?>