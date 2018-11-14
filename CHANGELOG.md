# ChangeLog

## 1.1.2 - (revision code: 2) 2018.10.15

* Fix import module loading error on ScorePackageValidator

## 1.1.1 - (revision code: 2) 2018.10.08

* Prevent SCORE from using block.hash and block.prev_hash

## 1.1.0 - (revision code: 2) 2018.10.08

### icon-service

* Fixed icx.send() return value bug
* Implemented call state reversion
* Limit the number of SCORE internal circular calls (Maximum: 64)
* Limit the number of SCORE internal calls (Maximum: 1024)
* Fixed a bug on SCORE zip file created on MacOS
* Fixed an exception which happens to IconServiceEngine._charge_transaction_fee() during invoking a block
* Implemented ScorePackageValidator and import whitelist
* Enable to change service configuration on runtime
* Keep state db consistency with revision code provided by Governance SCORE icx.send() return value bug
* Skip audit process for updating Governance SCORE
* Added unittest and integration test codes for error test cases
* Reuse cached invoke results

### developing SCORE

* Provide json_dumps, json_loads APIs to SCORE

## 1.0.6.2 2018.09.20

* Fixed an exception which happens to IconServiceEngine._charge_transaction_fee() during invoking a block
* Fixed a wrong message of "Out of Balance: balance(x) < value(y) + fee(y)" logging

## 1.0.6.1 - 2018.09.18

* Fix invoke error on calling readonly external call in icx_sendTransaction

## 1.0.6 - 2018.09.11

* Fixed a bug that icx is not transferred on calling the method provided by other SCORE
* rabbitmq connection check bugfix: connection close
* Removed unused package: jsonschema
* Removed debug assert code in icon_pre_validator.py
* Updated iconservice_cli log
* Updated pre-validator to reject a tx that has too long params compared to its stepLimit

## 1.0.5 - 2018.09.04

* Fixed intermittent SCORE module loading failures on Linux systems such as Jenkins
* Fixed rabbitmq initialize checking logic

## 1.0.4 - 2018.08.28

### icon-service

* Fixed error when calling ise_getStatus.
* TypeConverter raises an exception when None param is set
* When deployment is approved in audit mode, on_install or on_update is called in the deployer context(tx=None, msg=deployed msg).
* Disable transaction deploying SCORE with ICX value

### developing SCORE

* provide a hash API

## 0.9.4 - 2018-07-17

### icon-service

* Configurable parameters are separated from code, defined in file.
* Implemented blockchain governance, enforced by SCORE.
* SCORE update is now supported.
* Partial implementation of SCORE audit process.
* Fixed an issue arose when calling SCORE function without parameters.
* Added new transaction dataType, “message”.
* Undergoing transition from multiple SCORE DBs into a single DB.
* Fee and incentive structure (step rule) updated.

### developing SCORE

* init() parameters changed.
  - \_\_init\_\_(self, db: IconScoreDatabase)
  - Previous SCORE implementation must be updated.

## 0.9.3 - 2018-07-10

* Transaction fee model applied (Default mode: off)
* Version field added in icx_sendTransaction (See icx_sendTransaction API reference)
* Additional fields in TransactionResult (See icx_getTransactionResult API reference)
* Supports both protocol v2 and v3

## 0.9.2 - 2018-06-29

### icon-service

* loopchain is integrated with icon-service
* EventLog format changed
* JSON-RPC API v3 updated
  - Every protocol now has a version field.
  - Block information query API added
  - Transaction information query API added 

### developing SCORE

* InterfaceScore added
  - Other Score's external function can be called via Interface
* IconScore Coin API modified
  - self.send, self.transfer -> self.icx.send, self.icx.transfer

## 0.9.1 - 2018-06-11

### icon-service

* Return message of icx_sendTransaction method changed.
    - Error returns if the transaction is invalid.

### developing SCORE

* `@interface` decorator added
 
### Documents

* dapp_guid.md
    - Description added for SCORE built-in properties and functions. 

## 0.9.0 - 2018-06-01

### icon-service

* Logging feature added for SCORE development.

### developing SCORE

* IconScoreBase.genesis_init() changed to on_install(), on_update().
* SCORE can be implemented in multiple files.

## 0.8.1 - 2018-05-25

### icon-service

* Multiple SCOREs can be executed.
* When installing SCORE, previous DB state is kept. 
* DB related classes support bytes format data.

### developing SCORE

* @score decorator removed.
* @external() changed to @external.
* SCORE can be implemented in multiple files.

### Documents

* README.md content and file encoding changed.(cp949 -> utf-8)

## 0.8.0 - 2018-05-11

### icon-service

* Only single SCORE can be executed.
* When installing SCORE, DB state is cleared.

### developing SCORE

* SCORE should be implemented in a single file.
