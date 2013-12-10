<?php

include_once '../../includes/functions.php';

global $db;

switch ($_GET['action']) {
	
	case "autofix":
		global $config;
		
		$lazyCmd = $config::$lazy_exec;
		$tvshowFolder = $config::$tvshowsPath;
		
		$command = "$lazyCmd findmissing -v -s $tvshowFolder -f --type=3";
		print $command . " <br><br>";
		execInBackground($command);
		echo "A job has been launched which will try fix all missing epsiodes<br><br><br>PLEASE NOTE: It will NOT try download any missing seasons, it will only donwload missing epsiodes from seasons that already exist in your TVShow collection.<br><br><br>Check the jobs menu for the status of the job.";
		break;
		
		break;
		
	case "rpallmissing":
		global $config;
		
		$lazyCmd = $config::$lazy_exec;
		$tvshowFolder = $config::$tvshowsPath;
		
		$command = "$lazyCmd findmissing -v -s $tvshowFolder --type=4";
		print $command . " <br><br>";
		execInBackground($command);
		echo "A job has been launched which will check all shows for missing epsiodes or seasons.<br><br><br>Please check the jobs menu for the report when its completed.";
		break;
	
	case "download":
		
		$ftpMgr = new FTPManager();
		
		if (array_key_exists('torrent', $_POST)) {
			$torrents = $_POST['torrent'];
			
			//loop through each site
			foreach($torrents as $torrentSite => $torretsArray) {
				foreach($torretsArray as $torrent) {
					//start the download
					$result = $ftpMgr->sendFtpCommand("site torrent download $torrentSite $torrent");
					
					$path = false;
					$errMsg = true;
					
					foreach($result as $line) {
						if (preg_match('/200- Finished grabbing Torrent file. Now starting the torrent, when completed the files will show up under (.+)/', $line, $matches)) {
							$path = $matches[1];
						}	
						if (preg_match('/200- ERROR: (.+)/', $line, $matches)) {
							$errMsg = $matches[1];
						}
						
						if (preg_match('/ERROR: Torrent already downloaded here: (.+)/', $line, $matches)) {
							$path = $matches[1];
							$errMsg = false;
						}
						
					}
					
					if($path == false) {
						echo "Error downloading $torrent from $torrentSite... $errMsg<br>";
						continue;
					} else {
						//Lets add it to the download queue
						global $config;
						
						$lazycmd = $config::$lazy_exec;
						$command = "$lazycmd addrelease -r -d $path 2>&1";
					
						$result = shell_exec($command);
						
						$lines = explode(PHP_EOL, $result);
						$lazyErr = false;
						
						foreach ($lines as $line) {
							if (preg_match("/.+Download - ERROR - (.+)/", $line, $matches)) {
								$lazyErr = $matches[1];
							}
						}
						
						if ($lazyErr) {
							echo "Error adding release to the database $torrent.. $lazyErr<br>";
							continue;
						} else {
							//Wooohoo it was added
							echo "$torrent was added to the queue, it may take a little while to show up.<br>";
						}
					}
				}
			}
			
		}
		break;
		
	case "rpdeleteold":

		global $db;
		
		//First lets delete all the type = 2
		$sql = "select id from jobs where type = 2";
		foreach ($db->query($sql) as $row) {
			deleteJob($row['id']);
		}
		
		//$date = strtotime("-7 day", time());
		//$date = date('M d, Y', $date);
		
		//$sql = "select * from jobs where status = 1 finishDate > '$date'";
		//print $sql;
		
		//foreach ($db->query($sql) as $row) {
		//	print $row['id'];
		//	$command = "rm /home/media/.lazy/jobs/-job.job";
		//}
			
		
		break;

	case "rpdeleteall":
		$sql = "select * from jobs";

		
		foreach ($db->query($sql) as $row) {
			$id = $row['id'];
			try {
				deleteJob($id);
				echo "Deleted job id $id<br>";
			} catch (PDOException $e) {
				echo "Error deleting id: " . $id . " because " . $e->getMessage(); 
			}
		}
		

	case "rpdelete":
		if($_POST['item']){
			global $db;
			foreach($_POST['item'] as $id){
				//delete each $i with $i being the id
				try {
					deleteJob($id);
					echo "Deleted job id $id<br>";
				} catch (PDOException $e) {
					echo "Error deleting id: " . $id . " because " . $e->getMessage(); 
				}
			}
		}
				
		break;
		
		
	case "fix":
		
		if (array_key_exists('shows', $_POST)) {
			
			$output = '';
			
			foreach($_POST['shows'] as $showName => $show) {
				$fixSeasons = '';
				foreach($show as $season) {
					//We need to fix this season.. lets do it!
					$fixSeasons .= "$season,";
				}
				$fixSeasons = rtrim($fixSeasons, ',');
				
				
				global $config;
				
				$lazyCmd = $config::$lazy_exec;
				
				$command = "$lazyCmd findmissing -v -f --show=\"$showName\" --allseasons --seasons='$fixSeasons' -s /data/Videos/TVShows --type=1";
				echo "$command <br><br>";
				execInBackground($command);
				$output .= "Started job for $showName on seasons $fixSeasons<br><br>";
				
			}
			
			echo $output;
			echo 'NOTE: PLEASE CHECK THE RESULTS IN THE JOBS TAB.';
		}
		
		break;
	default:
		echo 'UNKNWON COMMAND';
		print_r($_POST);
}


function deleteJob($id) {
	global $db, $config;
	$sql = "delete from jobs where id = $id";
	$db->exec($sql);
		
	
	$filename = $config::$lazy_home . "/jobs/job-$id.job";
	$filename2 = $config::$lazy_home . "/jobs/job-$id.log";
	
	if (is_file($filename)) {
		unlink($filename);
	}
	
	if (is_file($filename2)) {
		unlink($filename2);
	}
	
}
?>