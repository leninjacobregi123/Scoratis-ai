'use strict';

var dsl = require('@maic/dsl');



Object.keys(dsl).forEach(function (k) {
	if (k !== 'default' && !Object.prototype.hasOwnProperty.call(exports, k)) Object.defineProperty(exports, k, {
		enumerable: true,
		get: function () { return dsl[k]; }
	});
});
//# sourceMappingURL=index.cjs.map
